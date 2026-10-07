/*
 * veldo-userns: the namespace helper of the agent sandbox (VELDO-0210 AC6).
 *
 * Installed root-owned at /usr/local/lib/veldo/veldo-userns by the owner's one-time setup, built
 * statically (no dynamic loader, so no LD_PRELOAD), run as the calling account, never setuid. The
 * host's AppArmor profile veldo-userns lets only this path create a user namespace; everything it
 * executes runs under the child profile veldo-userns-child, which denies every capability and
 * every user namespace.
 *
 * Usage: veldo-userns /absolute/path/agent_sandbox.py CONTEXT-DESCRIPTOR|selftest
 *
 * It does exactly this and nothing else:
 *   1. checks the entry point: an absolute canonical path to a regular file named agent_sandbox.py,
 *      owned by root or the calling account and writable by no other account (group write only
 *      for the caller's own primary group), in directories with the same property (or root-owned
 *      and sticky); the second argument is a descriptor number or "selftest";
 *   2. creates a user namespace and maps the calling uid and gid to themselves (setgroups denied);
 *   3. creates a mount and a PID namespace inside it and makes every mount private;
 *   4. forks the PID namespace's init, which waits until the parent has done step 5's first two
 *      parts, mounts a fresh procfs read only over /proc, drops every capability (bounding, ambient,
 *      effective, permitted and inheritable sets, securebits locked), sets no_new_privs and executes
 *      /usr/bin/python3 -I -S <entry> namespace-init <argument> with no environment but LC_CTYPE;
 *   5. in the parent, drops every capability the same way, closes every descriptor above stderr,
 *      relays TERM, INT and HUP (unless they were ignored when it started) to the init as SIGRTMIN,
 *      SIGRTMIN+1 and SIGRTMIN+2, and exits with the init's status.
 *
 * Build (reproducible: no timestamps, no paths, static):
 *   cc -std=c11 -O2 -Wall -Wextra -Werror -static -ffile-prefix-map="$PWD"=. -o veldo-userns veldo_userns.c
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <linux/capability.h>
#include <linux/securebits.h>
#include <sched.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#define PYTHON "/usr/bin/python3"
#define ENTRY_NAME "agent_sandbox.py"

static void fail(const char *step)
{
    fprintf(stderr, "veldo-userns: %s: %s\n", step, strerror(errno));
    _exit(2);
}

static void refuse(const char *why)
{
    fprintf(stderr, "veldo-userns: %s\n", why);
    _exit(2);
}

static void write_file(const char *path, const char *text)
{
    int fd = open(path, O_WRONLY | O_CLOEXEC);
    size_t length = strlen(text);
    if (fd < 0)
        fail(path);
    if (write(fd, text, length) != (ssize_t)length)
        fail(path);
    close(fd);
}

/* Owned by root or the caller; writable by no other account: not by others (unless a root-owned
 * sticky directory), and by its group only when that is the caller's own primary group. */
static void check_owner(const char *path, const struct stat *info, uid_t uid, gid_t gid, int directory)
{
    int sticky_root = directory && info->st_uid == 0 && (info->st_mode & S_ISVTX);
    int group_writable = (info->st_mode & 020) && info->st_gid != gid;
    if (info->st_uid != 0 && info->st_uid != uid) {
        fprintf(stderr, "veldo-userns: %s is owned by another account\n", path);
        _exit(2);
    }
    if (((info->st_mode & 002) || group_writable) && !sticky_root) {
        fprintf(stderr, "veldo-userns: %s is writable by another account\n", path);
        _exit(2);
    }
}

static void check_entry(const char *entry, uid_t uid, gid_t gid)
{
    char real[PATH_MAX], directory[PATH_MAX];
    struct stat info;
    const char *name;
    char *slash;

    if (entry[0] != '/')
        refuse("the entry point must be an absolute path");
    if (!realpath(entry, real) || strcmp(real, entry) != 0)
        refuse("the entry point must be a canonical path through no link");
    name = strrchr(entry, '/') + 1;
    if (strcmp(name, ENTRY_NAME) != 0)
        refuse("the entry point must be " ENTRY_NAME);
    if (lstat(entry, &info) != 0)
        fail(entry);
    if (!S_ISREG(info.st_mode))
        refuse("the entry point is not a regular file");
    check_owner(entry, &info, uid, gid, 0);
    strcpy(directory, entry);
    for (;;) {
        slash = strrchr(directory, '/');
        if (slash == directory)
            directory[1] = '\0';
        else
            *slash = '\0';
        if (lstat(directory, &info) != 0)
            fail(directory);
        if (!S_ISDIR(info.st_mode))
            refuse("a parent of the entry point is not a directory");
        check_owner(directory, &info, uid, gid, 1);
        if (slash == directory)
            break;
    }
}

static void check_argument(const char *argument)
{
    size_t length = strlen(argument);
    if (strcmp(argument, "selftest") == 0)
        return;
    if (length == 0 || length > 9 || strspn(argument, "0123456789") != length)
        refuse("the second argument must be a descriptor number or selftest");
}

/* Every capability, in every set, for good: securebits first (they need CAP_SETPCAP), then the
 * bounding set, the ambient set, the three process sets, and no_new_privs. */
static void drop_capabilities(void)
{
    struct __user_cap_header_struct header = {_LINUX_CAPABILITY_VERSION_3, 0};
    struct __user_cap_data_struct data[_LINUX_CAPABILITY_U32S_3];
    int capability;

    if (prctl(PR_SET_SECUREBITS, SECBIT_NOROOT | SECBIT_NOROOT_LOCKED | SECBIT_NO_SETUID_FIXUP
              | SECBIT_NO_SETUID_FIXUP_LOCKED | SECBIT_KEEP_CAPS_LOCKED | SECBIT_NO_CAP_AMBIENT_RAISE
              | SECBIT_NO_CAP_AMBIENT_RAISE_LOCKED, 0, 0, 0) != 0)
        fail("lock the securebits");
    for (capability = 0; prctl(PR_CAPBSET_READ, capability, 0, 0, 0) >= 0; capability++)
        if (prctl(PR_CAPBSET_DROP, capability, 0, 0, 0) != 0)
            fail("drop the bounding set");
    if (prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_CLEAR_ALL, 0, 0, 0) != 0)
        fail("clear the ambient set");
    memset(data, 0, sizeof data);
    if (syscall(SYS_capset, &header, data) != 0)
        fail("clear the capability sets");
    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0)
        fail("set no_new_privs");
}

int main(int argc, char **argv)
{
    static const int stops[] = {SIGTERM, SIGINT, SIGHUP};
    char map[64];
    int relay[3], gate[2], index, status;
    uid_t uid = getuid();
    gid_t gid = getgid();
    sigset_t waited;
    struct sigaction current;
    pid_t init;

    if (argc != 3)
        refuse("usage: veldo-userns /absolute/path/" ENTRY_NAME " CONTEXT-DESCRIPTOR|selftest");
    if (geteuid() != uid || getegid() != gid)
        refuse("runs as the calling account only");
    check_entry(argv[1], uid, gid);
    check_argument(argv[2]);
    if (prctl(PR_SET_PDEATHSIG, SIGKILL, 0, 0, 0) != 0)
        fail("PR_SET_PDEATHSIG");

    /* The stops, and the init's end, are taken with sigwaitinfo; the mask is inherited by the init. */
    sigemptyset(&waited);
    for (index = 0; index < 3; index++) {
        if (sigaction(stops[index], NULL, &current) != 0)
            fail("read a signal disposition");
        relay[index] = current.sa_handler != SIG_IGN;
        sigaddset(&waited, stops[index]);
    }
    sigaddset(&waited, SIGCHLD);
    if (sigprocmask(SIG_BLOCK, &waited, NULL) != 0)
        fail("block the stop signals");

    if (unshare(CLONE_NEWUSER) != 0)
        fail("create the user namespace");
    write_file("/proc/self/setgroups", "deny");
    snprintf(map, sizeof map, "%lu %lu 1\n", (unsigned long)uid, (unsigned long)uid);
    write_file("/proc/self/uid_map", map);
    snprintf(map, sizeof map, "%lu %lu 1\n", (unsigned long)gid, (unsigned long)gid);
    write_file("/proc/self/gid_map", map);
    if (getuid() != uid || getgid() != gid)
        refuse("the user namespace does not map this account to itself");
    if (unshare(CLONE_NEWNS | CLONE_NEWPID) != 0)
        fail("create the mount and PID namespaces");
    if (mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL) != 0)
        fail("make every mount private");

    /* The init waits on this until the parent holds no capability and no inherited descriptor. */
    if (pipe2(gate, O_CLOEXEC) != 0)
        fail("create the start gate");
    init = fork();
    if (init < 0)
        fail("fork the namespace's init");
    if (init == 0) {
        char *child_argv[] = {PYTHON, "-I", "-S", argv[1], "namespace-init", argv[2], NULL};
        char *child_env[] = {"LC_CTYPE=C.UTF-8", NULL};
        char byte;
        if (prctl(PR_SET_PDEATHSIG, SIGKILL, 0, 0, 0) != 0)
            fail("PR_SET_PDEATHSIG");
        close(gate[1]);
        while (read(gate[0], &byte, 1) < 0 && errno == EINTR)
            ;
        close(gate[0]);
        if (mount("proc", "/proc", "proc", MS_RDONLY | MS_NOSUID | MS_NODEV | MS_NOEXEC, NULL) != 0)
            fail("mount the namespace's procfs");
        drop_capabilities();
        execve(PYTHON, child_argv, child_env);
        fail("execute " PYTHON);
    }

    drop_capabilities();
    if (syscall(SYS_close_range, 3U, ~0U, 0U) != 0)
        fail("close the inherited descriptors");
    for (;;) {
        siginfo_t info;
        int number = sigwaitinfo(&waited, &info);
        if (number < 0) {
            if (errno == EINTR)
                continue;
            fail("wait for a signal");
        }
        if (number == SIGCHLD) {
            pid_t done = waitpid(init, &status, WNOHANG);
            if (done == init)
                _exit(WIFEXITED(status) ? WEXITSTATUS(status) : 1);
            continue;
        }
        for (index = 0; index < 3; index++)
            if (number == stops[index] && relay[index])
                kill(init, SIGRTMIN + index);
    }
}
