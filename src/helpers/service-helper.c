/*
 * Copyright (C) 2017 Extreme Networks, Inc.
 *
 * Snap service helper.
 *
 * This function is used to help a snap start up services.
 *
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <syslog.h>
#include <argp.h>
#include <time.h>
#include <fcntl.h>
#include <wordexp.h>
#include <semaphore.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <systemd/sd-daemon.h>
#include <bsd/libutil.h>

typedef enum {
  WAITCMD,
  EXECCMD,
  SPAWNCMD,
} cmdtype_t;

#define MYNAME "snap-service-helper"
#define HELPER_DIR "/" MYNAME
#define HELPER_STATUS_NONE        "0:none"
#define HELPER_STATUS_LOADED      "1:loaded"
#define HELPER_STATUS_WAIT        "2:waiting"
#define HELPER_STATUS_PRE         "3:preexec"
#define HELPER_STATUS_CMD         "4:exec"
#define HELPER_STATUS             "6:status="
#define HELPER_STATUS_STATUS_FAIL "7:status=FAIL"
#define HELPER_STATUS_STATUS_OK   "8:status=OK"
#define STATUS_SIZE 32
static char helperPath[256] = {0};

#define PID_DIR "/var/run/opx/pids/"
struct pidfh *pidfh = NULL;
static char pidPath[256] = {0};

#define SEM_NAME "/openswitch_semaphore"

#define printf(fmt, args...) syslog(LOG_INFO, "%s: " fmt, id, args)

#define STATE_LOADED  "LoadState=loaded"
#define STATE_RUNNING "SubState=running"
#define STATE_DEAD    "SubState=dead"
#define EXEC_STATUS_0 "ExecMainStatus=0"

static int verbose = 0;
static const char *id = NULL;
static const char *snap;
static const char *snapName;
static const char *snapData;

static char doc[] = "This daemon's ID.";
static char args_doc[] = "ID";

static struct argp_option options[] = {
  {"oneshot",  '1', 0,            0, "This is a 1-shot command."},
  {"after",    'a', "SVC",        0, "After service loaded."},
  {"cmd",      'c', "CMD",        0, "Primary command and args."},
  {"delay",    'd', "SECONDS",    0, "Delay start (in seconds)."},
  {"env",      'e', "ENV FILE",   0, "Supplemental environment file."},
  {"follows",  'f', "SVC",        0, "After one-shot service completes successfully."},
  {"init",     'i', "INIT",       0, "Initialization command."},
  {"pidfile",  'm', "PID FILE",   0, "Override the default pidfile."},
  {"notify",   'n', 0,            0, "The helper performs the systemd notify."},
  {"precmd",   'p', "CMD String", 0, "Command and args to execute before main command."},
  {"requires", 'r', "SVC",        0, "Required service running."},
  {"timeout",  't', "SECONDS",    0, "Timeout (in seconds)."},
  {"verbose",  'v', 0,            0, "Verbose processing."},
  { 0 }
};

#define MAX_PRE_CMDS 16
struct args
{
  int notify;
  int oneshot;
  char *init;
  char *pidfile;
  char *precmd[MAX_PRE_CMDS];
  char *cmd;
  char *requires;
  char *after;
  char *follows;
  long timeout;
  long delay;
};
static struct args args = {0};

#define DELIMS " \t\n="
static error_t process_env(const char *path)
{
  char line[256];
  char *tok, *name, *val;
  int status = 0;
  FILE *fp = fopen(path, "r");
  wordexp_t words = {0};

  if (verbose)
    printf("ENV: Importing %s\n", path);

  if (!fp) {
    printf("Error %d opening env file %s\n", errno, path);
    goto error_exit;
  }
  while (fgets(line, sizeof(line), fp)) {
    name = val = NULL;
    for (tok = strtok(line, DELIMS); tok; tok = strtok(NULL, DELIMS)) {
      if (*tok == '#')
        break;
      else if (strcmp(tok, "export") == 0)
        continue;
      else if (!name)
        name = tok;
      else if (!val)
        val = tok;
      else
        goto error_exit;
    }
    if (!name && !val)
      continue;
    else if (!name || !val) {
      printf("%s:%d %s=%s\n", __FUNCTION__, __LINE__, name, val);
      goto error_exit;
    }
    status = wordexp(val, &words, WRDE_UNDEF);
    if (status) {
      printf("Error %d expanding %s.\n", status, val);
      goto error_exit;
    }
    val = words.we_wordv[0];
    if (setenv(name, val, 1)) {
      printf("%s:%d ERROR %d setting env %s=%s\n", __FUNCTION__, __LINE__,
             errno, name, val);
      goto error_exit;
    } else {
      if (verbose)
        printf("ENV %s=%s\n", name, val);
    }
    wordfree(&words);
  }

 exit:
  wordfree(&words);
  if (fp)
    fclose(fp);
  return status;
error_exit:
  status = -1;
  goto exit;
}

static error_t parse_opt(int key, char *arg, struct argp_state *state)
{
  struct args *args = state->input;

  switch (key) {
  case '1':
    args->oneshot = 1;
    break;
  case 'a':
    args->after = arg;
    break;
  case 'c':
    args->cmd = arg;
    break;
  case 'd':
    args->delay = strtol(arg, NULL, 0);
    break;
  case 'e':
    return process_env(arg);
    break;
  case 'f':
    args->follows = arg;
    break;
  case 'i':
    args->init = arg;
    break;
  case 'm':
    args->pidfile = arg;
    break;
  case 'n':
    args->notify = 1;
    break;
  case 'p':
    {
      int i;
      for (i = 0; (i < (MAX_PRE_CMDS-1)) && args->precmd[i]; i++);
      args->precmd[i] = arg;
    }
    break;
  case 'r':
    args->requires = arg;
    break;
  case 't':
    args->timeout = strtol(arg, NULL, 0);
    break;
  case 'v':
    verbose = 1;
    break;
  case ARGP_KEY_ARG:
    if (state->arg_num >= 1)
      argp_usage(state);
    id = arg;
    break;
  case ARGP_KEY_END:
    if (state->arg_num < 1)
      argp_usage(state);
    break;
  default:
    return ARGP_ERR_UNKNOWN;
  }
  return 0;
}

static char *getHelperPath(const char *fname)
{
  static char path[256];
  strncpy(path, helperPath, sizeof(path));
  if (fname) {
    strncat(path, "/", sizeof(path) - strlen(path) - 1);
    strncat(path, fname, sizeof(path) - strlen(path) - 1);
  }
  return path;
}

static char *getStatus(const char *service)
{
  static char status[STATUS_SIZE];
  FILE *fp;
  char *path = getHelperPath(service);

  if (verbose)
    printf("GET STATUS in %s\n", path);

  fp = fopen(path, "r");
  if (fp) {
    status[0] = '\0';
    fgets(status, STATUS_SIZE, fp);
    fclose(fp);
  } else {
    strncpy(status, HELPER_STATUS_NONE, sizeof(status));
  }
  return status;
}

static void putStatus(const char *status)
{
  char *path = getHelperPath(id);
  FILE *fp = fopen(path, "w");

  if (fp) {
    if (verbose)
      printf("STATUS %s set in %s\n", status, path);
    fputs(status, fp);
    fclose(fp);
  }
}

static error_t waitforstatus(const char *service, const char *status, long timeout)
{
  int retry = 0;
  char *sstatus;

  do {
    if (retry)
      sleep(1);
    sstatus = getStatus(service);
    if (verbose)
      printf("%d: Waiting for %s property %s - current: %s\n",
             retry, service, status, sstatus);
    if (strlen(sstatus) && (strcmp(sstatus, status) >= 0))
      break;
  } while (++retry <= timeout);
  if (retry > timeout) {
    printf("Timed out waiting for %s property %s\n", service, status);
    return -1;
  } else {
    if (verbose)
      printf("WAIT - %s property: %s\n", service, status);
    return 0;
  }
  return (retry >= timeout ? -1 : 0);
}

#ifdef LATER
static error_t getServiceProperty(const char *service, const char *propname,
                                  char *property, size_t max)
{
  FILE *fp;
  error_t rc = 0;
  char svcname[80];
  char sdcmd[256];

  *property = '\0';
  snprintf(svcname, sizeof(svcname), "snap.%s.%s", snapName, service);
  snprintf(sdcmd, sizeof(sdcmd), "systemctl show -p %s %s", propname, svcname);

  fp = popen(sdcmd, "r");
  if (fp == NULL) {
    printf("Error %d executing cmd=%s\n", errno, sdcmd);
    return -1;
  }
  if (fgets(property, max-1, fp) == NULL) {
    printf("Error %d reading output from cmd=%s\n", errno, sdcmd);
    return -1;
  }

  return rc;
}

static error_t waitfor(char *service, char *property, int timeout)
{
  int retry;
  error_t rc = 0;
  char propname[80];
  char sdproperty[256];
  char *ltrimmed;
  char *tok;

  if (strcmp(property, STATE_LOADED) == 0)
    return waitforstatus(service, HELPER_STATUS_LOADED, timeout);
  else if (strcmp(property, STATE_DEAD) == 0)
    return waitforstatus(service, HELPER_STATUS, timeout);
  else if (strcmp(property, EXEC_STATUS_0) == 0)
    return waitforstatus(service, HELPER_STATUS_STATUS_OK, 0);

  strncpy(propname, property, sizeof(propname));
  propname[sizeof(propname)-1] = '\0';
  if ((tok = strchr(propname, '=')))
    *tok = '\0';
  for (retry = 0; retry < timeout; retry++) {
    rc = getServiceProperty(service, propname, sdproperty, sizeof(sdproperty));
    if (rc)
      break;
    for (ltrimmed = sdproperty;
         *ltrimmed && isspace((unsigned char)*ltrimmed);
         ltrimmed++);
    if (verbose) {
      printf("%d - Waiting for %s property %s - current: %s\n",
             retry, service, property, ltrimmed);
    }
    if (strstr(ltrimmed, property) == ltrimmed)
      break;
    sleep(1);
  }
  if (retry >= timeout) {
    printf("Timed out waiting for %s property %s\n", service, property);
    rc = -1;
  } else if (rc != 0) {
    printf("Error %d while waiting for %s property %s\n",
           rc, service, property);
  } else if (verbose) {
    printf("WAIT - %s property: %s\n", service, property);
  }
  return rc;
}
#endif

static error_t dowait(void)
{
  error_t status = 0;

  putStatus(HELPER_STATUS_WAIT);
  if (args.follows && (status == 0)) {
    if (verbose)
      printf("FOLLOWS %s - timeout = %ld\n", args.follows, args.timeout);
    status = waitforstatus(args.follows, HELPER_STATUS, args.timeout);
    if (status != 0) {
      printf("%s:%d status=%d\n",  __FUNCTION__, __LINE__, status);
      return status;
    }
    status = waitforstatus(args.follows, HELPER_STATUS_STATUS_OK, 0);
    if (status != 0) {
      printf("%s:%d status=%d\n", __FUNCTION__, __LINE__, status);
      return status;
    }
  }
  if (args.after && (status == 0)) {
    if (verbose)
      printf("AFTER %s - timeout = %ld\n", args.after, args.timeout);
    status = waitforstatus(args.after, HELPER_STATUS_LOADED, args.timeout);
    if (status != 0) {
      printf("%s:%d status=%d\n", __FUNCTION__, __LINE__, status);
      return status;
    }
  }
  if (args.requires && (status == 0)) {
    if (verbose)
      printf("REQUIRES %s - timeout = %ld\n", args.requires, args.timeout);
    status = waitforstatus(args.requires, HELPER_STATUS_LOADED, args.timeout);
    if (status != 0) {
      printf("%s:%d status=%d\n", __FUNCTION__, __LINE__, status);
      return status;
    }
    status = waitforstatus(args.requires, HELPER_STATUS_CMD, args.timeout);
    if (status != 0) {
      printf("%s:%d status=%d\n", __FUNCTION__, __LINE__, status);
      return status;
    }
  }

  return status;
}

static error_t docmd(char *cmdstr, cmdtype_t type)
{
  char cmd[512];
  char *cmdargs[32];
  int ignoreStatus = 0;
  error_t status = 0;
  pid_t pid = 0;
  int i;

  if (!cmdstr || !strlen(cmdstr))
    goto exit;

  /* ltrim whitespace */
  while (*cmdstr && isblank(*cmdstr))
    cmdstr++;

  /* Ignore status? */
  if (*cmdstr == '-') {
    ignoreStatus = 1;
    cmdstr++;
  }

  /* Tokenize */
  strncpy(cmd, cmdstr, sizeof(cmd));
  memset(cmdargs, 0, sizeof(cmdargs));
  cmdargs[0] = strtok(cmd, " \n\t");
  for (i = 1; i < ((sizeof(cmdargs)/sizeof(cmdargs[0])) - 1); i++) {
    if ((cmdargs[i] = strtok(NULL, " \n\t")) == NULL)
      break;
  }

  /* Fork */
  switch (type) {
  case WAITCMD:
  case SPAWNCMD:
    pid = fork();
    if (pid < 0)
      goto exit;
  case EXECCMD:
    break;
  }

  /* Execute */
  if (pid == 0) {
    if (pidfh)
      pidfile_close(pidfh);
    status = execv(cmdargs[0], cmdargs);
    if (status != 0)
      printf("Error (%d) executing command!!!\n", errno);
      goto exit;
  }

  switch (type) {
  case WAITCMD:
    if (pid) {
      int wstatus;
      waitpid(pid, &wstatus, 0);
      if (WIFEXITED(wstatus)) {
        status = ignoreStatus ? 0 : WEXITSTATUS(wstatus);
      }
      else {
        status = -1;
        printf("Error %d waiting on pid %d\n", wstatus, pid);
      }
    }
  case SPAWNCMD:
  case EXECCMD:
    break;
  }

 exit:
  return status;
}

static error_t mkdirs(const char *dir, const mode_t mode)
{
  char tmp[256];
  char *p = NULL;
  size_t len;
  error_t rc;

  snprintf(tmp, sizeof(tmp), "%s", dir);
  len = strlen(tmp);
  if (tmp[len-1] == '/')
    tmp[len-1] = '\0';
  for (p = tmp + 1; *p; p++) {
    if (*p == '/') {
      *p = '\0';
      mkdir(tmp, mode);
      *p = '/';
    }
  }
  rc = mkdir(tmp, mode);
  if (rc && (errno == EEXIST))
    rc = 0;
  if (rc != 0) {
    printf("%s:%d status=%d errno=%d dir=%s\n",
           __FUNCTION__, __LINE__, rc, errno, dir);
  }
  return rc;
}

static error_t init(void)
{
  error_t status = 0;

  snap = getenv("SNAP");
  if (!snap)
    snap = "";
  snapName = getenv("SNAP_NAME");
  if (!snapName)
    snapName = "NoSnap";
  snapData = getenv("SNAP_DATA");
  if (!snapData)
    snapData = "";

  openlog(MYNAME,  LOG_CONS | LOG_PID | LOG_NDELAY, LOG_LOCAL1);

  /* Create the helper status file */
  helperPath[sizeof(helperPath)-1] = '\0';
  strncpy(helperPath, snapData, sizeof(helperPath));
  strncat(helperPath, HELPER_DIR, sizeof(helperPath) - strlen(helperPath) - 1);
  status = mkdirs(helperPath, S_IRWXU);
  if (status != 0) {
    printf("Error (%d) creating dir %s\n", errno, helperPath);
    goto exit;
  }
  putStatus(HELPER_STATUS_LOADED);

  /* Create the pidfile */
  pidPath[sizeof(pidPath)-1] = '\0';
  if (args.pidfile)
    strncpy(pidPath, args.pidfile, sizeof(pidPath)-1);
  else {
    strncpy(pidPath, snapData, sizeof(pidPath));
    strncat(pidPath, PID_DIR, sizeof(pidPath) - strlen(pidPath) - 1);
    status = mkdirs(pidPath, S_IRWXU);
    if (status != 0) {
      printf("Error (%d) creating PID dir %s\n", errno, pidPath);
      goto exit;
    }
    strncat(pidPath, id, sizeof(pidPath) - strlen(pidPath) - 1);
  }

  pidfh = pidfile_open(pidPath, 0644, NULL);
  if (!pidfh) {
    printf("Error (%d) creating pid %s\n", errno, pidPath);
    status = -1;
    goto exit;
  } else {
    if (verbose)
      printf("Using PID File %s\n", pidPath);
    status = 0;
  }
  pidfile_write(pidfh);

  /* The init command is mutually exclusive */
  if (args.init) {
    sem_t *sem = NULL;

    /* Create/Open the sempahore file */
    sem = sem_open(SEM_NAME, O_CREAT, S_IRUSR | S_IWUSR, 1);
    if (sem == SEM_FAILED) {
      status = -1;
      printf("Error (%d) creating semaphore %s\n", errno, SEM_NAME);
      goto exit;
    }

    /* Grab the sempahore */
    status = sem_wait(sem);
    if (status != 0) {
      printf("Error (%d) grabbing semaphore %s\n", errno, SEM_NAME);
      goto exit;
    }

    /* Execute init under protection of sempahore */
    status = docmd(args.init, WAITCMD);

    /* Release and close the semaphore */
    sem_post(sem);
    sem_close(sem);

    /* Check the status returned from the init command */
    if (status != 0) {
      printf("Error (%d) executing initialization: %s\n", errno, args.init);
    }
  }

 exit:
  return status;
}

static struct argp argp = { options, parse_opt, doc, args_doc };

int main(int argc, char **argv)
{
  error_t status;

  /* Parse args */
  args.timeout = 60;
  argp_parse(&argp, argc, argv, 0, 0, &args);

  /* Initialize environment vars, logging, and status */
  status = init();
  if (status != 0) {
    printf("%s:%d status=%d errno=%d\n", __FUNCTION__, __LINE__, status, errno);
    goto exit;
  }

  /* If the helper is supposed to notify, do it now before waiting. */
  if (args.notify) {
    /* Per manpage, ignore return value of this call. */
    sd_notify(0, "READY=1");
  }

  /* Perform any waiting */
  status = dowait();
  if (status != 0) {
    printf("%s:%d status=%d errno=%d\n", __FUNCTION__, __LINE__, status, errno);
    goto exit;
  }

  /* Pre-exec */
  for (int i = 0; (i < MAX_PRE_CMDS) && args.precmd[i]; i++) {
    putStatus(HELPER_STATUS_PRE);
    if (verbose)
      printf("PRE-CMD - %s\n", args.precmd[i]);
    status = docmd(args.precmd[i], WAITCMD);
    if (status != 0) {
      printf("%s:%d status=%d errno=%d\n", __FUNCTION__, __LINE__, status, errno);
      goto exit;
    }
  }

  /* Primary command */
  putStatus(HELPER_STATUS_CMD);
  if (args.delay) {
    if (verbose)
      printf("Delay command execution for %ld seconds.\n", args.delay);
    sleep(args.delay);
  }
  if (verbose)
    printf("CMD - %s\n", args.cmd);
  status = docmd(args.cmd, args.oneshot ? WAITCMD : EXECCMD);
  if (status != 0) {
    printf("%s:%d status=%d errno=%d\n", __FUNCTION__, __LINE__, status, errno);
    goto exit;
  }

 exit:
  if (pidfh) {
    pidfile_close(pidfh);
    pidfile_remove(pidfh);
  }
  putStatus(status ? HELPER_STATUS_STATUS_FAIL : HELPER_STATUS_STATUS_OK);
  closelog();
  exit(status);
}
