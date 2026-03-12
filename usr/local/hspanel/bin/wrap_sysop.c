#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/*
 * wrap_sysop.c - HS-Panel privileged operation wrapper
 *
 * Build and deploy as setuid root (4755). Only explicit allowlisted commands
 * are executable. No shell invocation is used.
 */

static int is_safe_username(const char *value) {
  size_t i;
  size_t len;

  if (value == NULL) {
    return 0;
  }

  len = strlen(value);
  if (len == 0 || len > 64) {
    return 0;
  }

  for (i = 0; i < len; i++) {
    char c = value[i];
    if (!(isalnum((unsigned char)c) || c == '_' || c == '-' || c == '.')) {
      return 0;
    }
  }
  return 1;
}

static int is_safe_path(const char *value) {
  size_t i;
  size_t len;

  if (value == NULL) {
    return 0;
  }

  len = strlen(value);
  if (len == 0 || len > 255 || value[0] != '/') {
    return 0;
  }

  for (i = 0; i < len; i++) {
    char c = value[i];
    if (!(isalnum((unsigned char)c) || c == '/' || c == '_' || c == '-' || c == '.')) {
      return 0;
    }
  }
  return 1;
}

static int run_execv(const char *path, char *const cmd_argv[]) {
  execv(path, cmd_argv);
  perror("execv");
  return 1;
}

static void print_usage(const char *binary) {
  fprintf(stderr, "Usage: %s <operation> [args...]\n", binary);
  fprintf(stderr, "Allowed operations:\n");
  fprintf(stderr, "  reload_lsws\n");
  fprintf(stderr, "  reload_postfix\n");
  fprintf(stderr, "  reload_dovecot\n");
  fprintf(stderr, "  reload_pdns\n");
  fprintf(stderr, "  reload_csf\n");
  fprintf(stderr, "  restart_pureftpd\n");
  fprintf(stderr, "  useradd <username> <home_dir>\n");
  fprintf(stderr, "  userdel <username>\n");
}

int main(int argc, char *argv[]) {
  const char *operation;

  if (setgid(0) != 0 || setuid(0) != 0) {
    fprintf(stderr, "Error: setuid/setgid root failed. Ensure binary is 4755 root.\n");
    return 1;
  }

  if (argc < 2) {
    print_usage(argv[0]);
    return 1;
  }

  operation = argv[1];

  if (strcmp(operation, "reload_lsws") == 0) {
    char *const cmd[] = {"/usr/local/lsws/bin/lswsctrl", "restart", NULL};
    return run_execv(cmd[0], cmd);
  }

  if (strcmp(operation, "reload_postfix") == 0) {
    char *const cmd[] = {"/bin/systemctl", "reload", "postfix", NULL};
    return run_execv(cmd[0], cmd);
  }

  if (strcmp(operation, "reload_dovecot") == 0) {
    char *const cmd[] = {"/bin/systemctl", "reload", "dovecot", NULL};
    return run_execv(cmd[0], cmd);
  }

  if (strcmp(operation, "reload_pdns") == 0) {
    char *const cmd[] = {"/bin/systemctl", "reload", "pdns", NULL};
    return run_execv(cmd[0], cmd);
  }

  if (strcmp(operation, "reload_csf") == 0) {
    char *const cmd[] = {"/usr/sbin/csf", "-r", NULL};
    return run_execv(cmd[0], cmd);
  }

  if (strcmp(operation, "restart_pureftpd") == 0) {
    char *const cmd[] = {"/bin/systemctl", "restart", "pure-ftpd", NULL};
    return run_execv(cmd[0], cmd);
  }

  if (strcmp(operation, "useradd") == 0) {
    if (argc != 4) {
      fprintf(stderr, "Usage: %s useradd <username> <home_dir>\n", argv[0]);
      return 1;
    }
    if (!is_safe_username(argv[2]) || !is_safe_path(argv[3])) {
      fprintf(stderr, "Invalid useradd arguments\n");
      return 1;
    }

    char *const cmd[] = {
      "/usr/sbin/useradd",
      "-m",
      "-d",
      argv[3],
      "-s",
      "/bin/bash",
      argv[2],
      NULL
    };
    return run_execv(cmd[0], cmd);
  }

  if (strcmp(operation, "userdel") == 0) {
    if (argc != 3) {
      fprintf(stderr, "Usage: %s userdel <username>\n", argv[0]);
      return 1;
    }
    if (!is_safe_username(argv[2])) {
      fprintf(stderr, "Invalid username\n");
      return 1;
    }
    char *const cmd[] = {"/usr/sbin/userdel", "-r", argv[2], NULL};
    return run_execv(cmd[0], cmd);
  }

  fprintf(stderr, "Unknown operation: %s\n", operation);
  print_usage(argv[0]);
  return 1;
}
