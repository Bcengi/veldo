/*
 * veldo-procread: the process reader of space management (VELDO-0344, design section 7.1).
 *
 * Installed root-owned at /usr/local/lib/veldo/veldo-procread by the owner's one-time setup
 * (docs/veldo-procread-setup.txt), group the owner's own, mode 0750, with the one file capability
 * cap_sys_ptrace=ep. Built statically: no loader runs and no library can be put in front of it.
 * It is started by the user unit veldo-procread@.service, one instance per connection, with the
 * connection as its standard output. It is never setuid.
 *
 * Usage: veldo-procread        (no argument; with any argument it prints nothing and exits 2)
 *
 * It does exactly this and nothing else:
 *   1. reads which capabilities it holds (capget), ignores SIGPIPE so that a closed connection is
 *      a failed write and not a signal, sets no_new_privs and installs a seccomp filter. From
 *      here the kernel ends the process on every call the filter does not allow;
 *   2. opens /proc and asks the kernel what it is (fstatfs). When it is not the process file
 *      system it writes nothing and exits 4;
 *   3. writes the header line, veldo-procread 1 cap=C, C being 1 when cap_sys_ptrace is in its
 *      effective set, and then makes one blocking read on descriptor 1. It goes on whatever that
 *      read returns: the probe is the side that refuses a table sent too early;
 *   4. for every process of the table that is not a kernel thread reads stat (the start time and
 *      the flags), mountinfo (the device of each mount id), then for every task under its task
 *      folder the working directory by stat, the run label in environ (THE RUN LABEL, below;
 *      beside it the task's own stat and its exe by stat, before the read and after it) and every
 *      fdinfo entry, lists the task folder a second time, and reads maps. It prints the lines
 *      below and opens nothing outside /proc;
 *   5. writes the end line, makes one blocking read on descriptor 1 and exits 0 when that read
 *      returns, which is when the probe has shut down its side: the writer of a short output is
 *      still alive when the probe looks.
 *
 * A write that fails ends it at once with exit status 3 and no end line. A short write is
 * continued until every byte is out.
 *
 * The output: ASCII lines ending in a line feed, fields separated by one space, every number
 * decimal.
 *   veldo-procread 1 cap=C          the first line (3)
 *   p PID START                     opens the block of one process; START is field 22 of stat
 *   t TID                           opens the facts of one task; the first is the first thread
 *   c MAJOR:MINOR INODE             the working directory of the task
 *   l -                             the environment of the task was read whole, of one program
 *                                   (A WHOLE READ, below), and no entry of it is the run label
 *                                   variable
 *   l =HEX                          one entry of the task's environment is the run label variable;
 *                                   HEX is its value, two lower-case hexadecimal digits a byte, and
 *                                   nothing for an empty value. One line for each such entry
 *   f FD MOUNT MAJOR:MINOR INODE    one open descriptor of the task; the device is a single
 *                                   hyphen when the process's mountinfo has no row for MOUNT
 *   m MAJOR:MINOR INODE             one mapped file of the process, after its last task; lines
 *                                   of maps with inode 0 are left out
 *   x FACT ERRNO                    a fact that could not be read: cwd, env or fd of the task it
 *                                   follows; stat, mnt, maps or task of the process. x task 0 is
 *                                   a task the second listing showed and the reader had not read.
 *                                   Error 12 is also written when a table of this program is full,
 *                                   x env 7 for a run label longer than 64 bytes, and x env 11
 *                                   for an environment that was not read whole, of one program
 *   g                               the process ended while it was read; closes its block
 *   end COUNT                       the last line; COUNT is the number of p lines
 * A c, f or m line equal to one the block already holds is not written again. A task that has
 * ended when it is read gets no line, and one that ends before its environment is opened gets no
 * l line. Nothing is written to standard error.
 *
 * THE RUN LABEL. A wrapped run gives its command one variable, VELDO_SPACE_LABEL, whose value is
 * the run (bin/veldo, SPACE_LABEL_VARIABLE; control_space_docker.py, LABEL_VARIABLE). Whether a
 * process carries it decides whether a run is over, and for a process the probing user may not
 * read, nothing but this program can say. So for every task it reads, it reads the task's environ
 * entry and prints the value of that one variable and nothing else of it: an entry is compared
 * with the name and its equals sign byte by byte, the bytes of every other entry are passed over
 * and never copied, kept or printed, and the name of no other variable is in this source. The
 * buffer the entry was read through is cleared before the next file is opened. A value is at most
 * 64 bytes; a longer one is not printed, in part or whole, and the fact is unread (x env 7). The
 * value is printed in hexadecimal, so no byte of another process reaches a line as it is.
 *
 * A WHOLE READ. The kernel reads environ from the memory the task had when the entry was opened. A
 * task that executes a program between the open and the read has other memory by then, and the
 * read returns nothing, or a part; so does a read of memory that is no longer there. Bytes that
 * end early with no label among them are not an environment without the label. So before the read
 * and after it the reader takes what the task is: the start time and the bounds of the
 * environment (fields 22, 50 and 51 of the task's stat) and the device and inode of its exe. An l
 * line is written only when the two agree, the read returned at least one byte, and it returned
 * exactly as many as the bounds are apart. Otherwise the environment is read a second time, the
 * same way, and when that read is not whole either the fact is unread (x env 11) and no l line is
 * written. An l line is kept back until its read is known to be whole. An environment of no bytes
 * at all is never a whole read: the kernel returns the same nothing for a task that is executing.
 *
 * THE FILTER is a list of what is allowed, for the native architecture only (the x32 numbers
 * refused): openat with none of O_WRONLY, O_RDWR, O_CREAT and O_TRUNC, read, getdents64,
 * newfstatat, fstatfs, close, write to descriptor 1 and no other, exit and exit_group. Every other
 * call ends the process: ptrace, process_vm_readv, process_vm_writev, pidfd_open, pidfd_getfd,
 * kcmp, kill, tkill, tgkill, rt_sigqueueinfo, pidfd_send_signal and execve among them. The program
 * keeps everything in static storage, so no call for memory is allowed either. The filter cannot
 * see the path of an open, so it does not limit which entries are opened for reading; this source
 * does, and the pinned digest ties the installed binary to it.
 *
 * Build (reproducible: no timestamps, no paths, static), from the folder that holds the source:
 *   env -i PATH=/usr/bin:/bin /usr/bin/cc -std=c11 -O2 -Wall -Wextra -Werror -static \
 *       -ffile-prefix-map="$PWD"=. -o veldo-procread veldo_procread.c
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/audit.h>
#include <linux/capability.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <signal.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <sys/vfs.h>
#include <unistd.h>

#if defined(__x86_64__)
#define NATIVE_ARCH AUDIT_ARCH_X86_64
#elif defined(__aarch64__)
#define NATIVE_ARCH AUDIT_ARCH_AARCH64
#else
#error "veldo-procread is built for x86_64 and aarch64 only"
#endif

#define PROC_MAGIC 0x9fa0L          /* PROC_SUPER_MAGIC */
#define KERNEL_THREAD 0x00200000UL  /* PF_KTHREAD, in the flags of stat */
#define PTRACE_CAPABILITY 19        /* CAP_SYS_PTRACE */
#define WRITING (O_WRONLY | O_RDWR | O_CREAT | O_TRUNC)

#define LABEL_BYTES 64              /* the longest run label that is printed */

#define SLOTS (1u << 20)            /* the lines one block is compared with */
#define MOUNT_SLOTS (1u << 16)
#define TASKS (1u << 16)

/* The filter. Each group is whole in itself and leaves the call number loaded for the next. */
#define ARGUMENT(n) (offsetof(struct seccomp_data, args) + 8 * (n))
#define LOAD(where) BPF_STMT(BPF_LD | BPF_W | BPF_ABS, (where))
#define LOAD_CALL LOAD(offsetof(struct seccomp_data, nr))
#define END_PROCESS BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS)
#define ALLOWED BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW)
#define ALLOW(call) BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, (call), 0, 1), ALLOWED

static struct sock_filter filter[] = {
    LOAD(offsetof(struct seccomp_data, arch)),
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, NATIVE_ARCH, 1, 0),
    END_PROCESS,
    LOAD_CALL,
#if defined(__x86_64__)
    BPF_JUMP(BPF_JMP | BPF_JGE | BPF_K, 0x40000000u, 0, 1), /* an x32 call number */
    END_PROCESS,
#endif
    /* write, to descriptor 1 and no other */
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_write, 0, 6),
    LOAD(ARGUMENT(0)),
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, 1, 0, 3),
    LOAD(ARGUMENT(0) + 4),
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, 0, 0, 1),
    ALLOWED,
    END_PROCESS,
    LOAD_CALL,
    /* openat, for reading only */
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_openat, 0, 4),
    LOAD(ARGUMENT(2)),
    BPF_JUMP(BPF_JMP | BPF_JSET | BPF_K, WRITING, 1, 0),
    ALLOWED,
    END_PROCESS,
    LOAD_CALL,
    ALLOW(__NR_read),
    ALLOW(__NR_getdents64),
    ALLOW(__NR_newfstatat),
    ALLOW(__NR_fstatfs),
    ALLOW(__NR_close),
    ALLOW(__NR_exit),
    ALLOW(__NR_exit_group),
    END_PROCESS,
};

static void leave(int status)
{
    for (;;)
        syscall(SYS_exit_group, status);
}

/* Output: one buffer, written to descriptor 1. A failed write ends the reader. */
static char out[16384];
static size_t out_len;

static void flush(void)
{
    size_t done = 0;
    while (done < out_len) {
        long n = syscall(SYS_write, 1, out + done, out_len - done);
        if (n <= 0) {
            if (n < 0 && errno == EINTR)
                continue;
            leave(3);
        }
        done += (size_t)n;
    }
    out_len = 0;
}

static void put(const char *text, size_t length)
{
    if (out_len + length > sizeof out)
        flush();
    memcpy(out + out_len, text, length);
    out_len += length;
}

/* A line is put together here and written whole. */
static char line[160];
static size_t line_len;

static void word(const char *text)
{
    size_t length = strlen(text);
    memcpy(line + line_len, text, length);
    line_len += length;
}

static void number(uint64_t value)
{
    char digits[24];
    size_t count = 0;
    do {
        digits[count++] = (char)('0' + value % 10);
        value /= 10;
    } while (value);
    while (count)
        line[line_len++] = digits[--count];
}

static void finish(void)
{
    line[line_len++] = '\n';
    put(line, line_len);
    line_len = 0;
}

/* Paths under /proc, opened beneath the one descriptor of /proc. */
static char path[96];

static void path_start(uint64_t pid, const char *rest)
{
    line_len = 0;
    number(pid);
    word(rest);
    memcpy(path, line, line_len);
    path[line_len] = 0;
    line_len = 0;
}

static void path_task(uint64_t pid, uint64_t tid, const char *rest, int64_t entry)
{
    line_len = 0;
    number(pid);
    word("/task/");
    number(tid);
    word(rest);
    if (entry >= 0)
        number((uint64_t)entry);
    memcpy(path, line, line_len);
    path[line_len] = 0;
    line_len = 0;
}

static int open_under(int proc, int flags)
{
    return (int)syscall(SYS_openat, proc, path, O_RDONLY | O_CLOEXEC | O_NOCTTY | flags);
}

static int gone(int error)
{
    return error == ENOENT || error == ESRCH;
}

/* What `path` names, the last link followed. 0, or the error. */
static int stat_under(int proc, struct stat *found)
{
    return syscall(SYS_newfstatat, proc, path, found, 0) < 0 ? errno : 0;
}

/* Reading a file a byte at a time through one buffer. */
static struct {
    int fd;
    size_t at, length;
    uint64_t total; /* the bytes read from the file so far */
    int error;
    char bytes[65536];
} in;

static void in_start(int fd)
{
    in.fd = fd;
    in.at = in.length = 0;
    in.total = 0;
    in.error = 0;
}

static int in_byte(void)
{
    if (in.at == in.length) {
        long n;
        if (in.error)
            return -1;
        do {
            n = syscall(SYS_read, in.fd, in.bytes, sizeof in.bytes);
        } while (n < 0 && errno == EINTR);
        if (n <= 0) {
            in.error = n < 0 ? errno : -1; /* -1: the end of the file */
            return -1;
        }
        in.at = 0;
        in.length = (size_t)n;
        in.total += (uint64_t)n;
    }
    return (unsigned char)in.bytes[in.at++];
}

/* The next byte is kept here when a number ended on it. */
static int held = -2;

static int next(void)
{
    int byte;
    if (held != -2) {
        byte = held;
        held = -2;
        return byte;
    }
    return in_byte();
}

static int read_number(unsigned base, uint64_t *value)
{
    int byte, count = 0;
    *value = 0;
    for (;;) {
        unsigned digit;
        byte = next();
        if (byte >= '0' && byte <= '9')
            digit = (unsigned)(byte - '0');
        else if (base == 16 && byte >= 'a' && byte <= 'f')
            digit = (unsigned)(byte - 'a') + 10;
        else
            break;
        *value = *value * base + digit;
        count++;
    }
    held = byte;
    return count > 0;
}

static int skip_blanks(void)
{
    int byte;
    do {
        byte = next();
    } while (byte == ' ' || byte == '\t');
    held = byte;
    return byte;
}

static void skip_word(void)
{
    int byte;
    do {
        byte = next();
    } while (byte != ' ' && byte != '\t' && byte != '\n' && byte != -1);
    held = byte;
}

static void skip_line(void)
{
    int byte;
    do {
        byte = next();
    } while (byte != '\n' && byte != -1);
}

/* The lines the block already holds, and the tasks that were read: one table, emptied by a new
 * stamp for every process. */
static struct {
    uint64_t key[5];
    uint32_t stamp;
} slots[SLOTS];
static uint32_t stamp;
static uint32_t used;

/* 1 when the key is new and was added, 0 when the table holds it, -1 when the table is full. */
static int add(uint64_t kind, uint64_t a, uint64_t b, uint64_t c, uint64_t d, int insert)
{
    uint64_t hash = kind * 0x9e3779b97f4a7c15ULL;
    uint32_t at;
    hash = (hash ^ a) * 0xff51afd7ed558ccdULL;
    hash = (hash ^ b) * 0xc4ceb9fe1a85ec53ULL;
    hash = (hash ^ c) * 0x9e3779b97f4a7c15ULL;
    hash = (hash ^ d) * 0xff51afd7ed558ccdULL;
    at = (uint32_t)(hash >> 40) & (SLOTS - 1);
    for (;;) {
        if (slots[at].stamp != stamp) {
            if (!insert)
                return 1;
            if (used >= SLOTS / 2)
                return -1;
            slots[at].stamp = stamp;
            slots[at].key[0] = kind;
            slots[at].key[1] = a;
            slots[at].key[2] = b;
            slots[at].key[3] = c;
            slots[at].key[4] = d;
            used++;
            return 1;
        }
        if (slots[at].key[0] == kind && slots[at].key[1] == a && slots[at].key[2] == b
            && slots[at].key[3] == c && slots[at].key[4] == d)
            return 0;
        at = (at + 1) & (SLOTS - 1);
    }
}

/* The device of each mount id of the process. */
static struct {
    uint64_t id, major, minor;
    uint32_t stamp;
} mounts[MOUNT_SLOTS];
static uint32_t mounts_used;

static int mount_add(uint64_t id, uint64_t major, uint64_t minor)
{
    uint32_t at = (uint32_t)((id * 0x9e3779b97f4a7c15ULL) >> 40) & (MOUNT_SLOTS - 1);
    while (mounts[at].stamp == stamp) {
        if (mounts[at].id == id) { /* a later row of the same id replaces the earlier one */
            mounts[at].major = major;
            mounts[at].minor = minor;
            return 1;
        }
        at = (at + 1) & (MOUNT_SLOTS - 1);
    }
    if (mounts_used >= MOUNT_SLOTS / 2)
        return 0;
    mounts[at].stamp = stamp;
    mounts[at].id = id;
    mounts[at].major = major;
    mounts[at].minor = minor;
    mounts_used++;
    return 1;
}

static int mount_find(uint64_t id, uint64_t *major, uint64_t *minor)
{
    uint32_t at = (uint32_t)((id * 0x9e3779b97f4a7c15ULL) >> 40) & (MOUNT_SLOTS - 1);
    while (mounts[at].stamp == stamp) {
        if (mounts[at].id == id) {
            *major = mounts[at].major;
            *minor = mounts[at].minor;
            return 1;
        }
        at = (at + 1) & (MOUNT_SLOTS - 1);
    }
    return 0;
}

static void unread(const char *fact, int error)
{
    word("x ");
    word(fact);
    word(" ");
    number((uint64_t)error);
    finish();
}

/* The entries of a folder whose names are numbers, listed through `entries`: the process table, a
 * task folder and a folder of descriptors are listed inside one another, so each has a buffer of
 * its own. Returns 0, or the error. */
#define LISTING 32768
static char table_entries[LISTING], task_entries[LISTING], descriptor_entries[LISTING];

static int numbered(int folder, char *entries, void (*each)(uint64_t, void *), void *with)
{
    for (;;) {
        long at = 0, n = syscall(SYS_getdents64, folder, entries, LISTING);
        if (n < 0)
            return errno;
        if (n == 0)
            return 0;
        while (at < n) {
            /* struct linux_dirent64: inode 8, offset 8, record length 2, type 1, name */
            uint16_t length;
            const char *name = entries + at + 19;
            uint64_t value = 0;
            int digits = 0;
            memcpy(&length, entries + at + 16, sizeof length);
            while (*name >= '0' && *name <= '9') {
                value = value * 10 + (uint64_t)(*name++ - '0');
                digits++;
            }
            if (digits && !*name)
                each(value, with);
            at += length;
        }
    }
}

/* The stat entry `path` names: the start time and the flags, and with `bounds` the two ends of the
 * environment (fields 50 and 51). 0 read, else the error. */
static char text[4096];

static int read_stat(int proc, uint64_t *start, uint64_t *flags, uint64_t *bounds)
{
    long n, total = 0;
    int fd, field = 0;
    char *at, *end;
    fd = open_under(proc, 0);
    if (fd < 0)
        return errno;
    for (;;) {
        n = syscall(SYS_read, fd, text + total, sizeof text - 1 - (size_t)total);
        if (n < 0 && errno == EINTR)
            continue;
        if (n <= 0)
            break;
        total += n;
    }
    if (n < 0) {
        int error = errno;
        syscall(SYS_close, fd);
        return error;
    }
    syscall(SYS_close, fd);
    text[total] = 0;
    at = strrchr(text, ')'); /* the name may hold anything; the fields follow its last bracket */
    if (!at)
        return EINVAL;
    end = text + total;
    *start = *flags = 0;
    /* After the bracket: field 3 the state, then one field per blank; 9 the flags, 22 the start,
     * 50 and 51 the environment's first byte and the byte after its last. */
    for (at++, field = 2; at < end; at++) {
        if (*at != ' ')
            continue;
        field++;
        if (field == 9 || field == 22 || field == 50 || field == 51) {
            uint64_t value = 0;
            char *digit = at + 1;
            if (digit >= end || *digit < '0' || *digit > '9')
                return EINVAL;
            while (digit < end && *digit >= '0' && *digit <= '9')
                value = value * 10 + (uint64_t)(*digit++ - '0');
            if (field == 9)
                *flags = value;
            else if (field == 22) {
                *start = value;
                if (!bounds)
                    return 0;
            } else if (field == 50)
                bounds[0] = value;
            else {
                bounds[1] = value;
                return 0;
            }
        }
    }
    return EINVAL;
}

/* mountinfo: ID PARENT MAJOR:MINOR ... per line. 0 read, else the error. */
static int read_mounts(int proc, uint64_t pid)
{
    int fd, error = 0;
    path_start(pid, "/mountinfo");
    fd = open_under(proc, 0);
    if (fd < 0)
        return errno;
    in_start(fd);
    held = -2;
    for (;;) {
        uint64_t id, parent, major, minor;
        if (skip_blanks() == -1)
            break;
        if (!read_number(10, &id) || next() != ' ' || !read_number(10, &parent) || next() != ' '
            || !read_number(10, &major) || next() != ':' || !read_number(10, &minor)) {
            error = EINVAL;
            break;
        }
        if (!mount_add(id, major, minor)) {
            error = ENOMEM;
            break;
        }
        skip_line();
    }
    if (!error && in.error > 0)
        error = in.error;
    syscall(SYS_close, fd);
    return error;
}

/* One fdinfo entry: the mount id and the inode number. 0 read, else the error. */
static int read_fdinfo(int proc, uint64_t *mount, uint64_t *inode)
{
    int fd = open_under(proc, 0), have_mount = 0, have_inode = 0;
    if (fd < 0)
        return errno;
    in_start(fd);
    held = -2;
    for (;;) {
        char name[8];
        int byte, length = 0;
        while ((byte = next()) != -1 && byte != ':' && byte != '\n')
            if (length < 7)
                name[length++] = (char)byte;
        name[length] = 0;
        if (byte == -1)
            break;
        if (byte == ':' && !strcmp(name, "mnt_id")) {
            skip_blanks();
            have_mount = read_number(10, mount);
        } else if (byte == ':' && !strcmp(name, "ino")) {
            skip_blanks();
            have_inode = read_number(10, inode);
        }
        if (byte != '\n')
            skip_line();
        if (have_mount && have_inode)
            break;
    }
    syscall(SYS_close, fd);
    if (in.error > 0)
        return in.error;
    return have_mount && have_inode ? 0 : ENODATA;
}

/* The one variable of another process's environment this program prints the value of. */
static const char label_name[] = "VELDO_SPACE_LABEL=";

/* The l lines of one read, kept back until the read is known to be whole. */
static char kept[8192];
static size_t kept_len;

/* environ of the task `path` names: the value of each entry that is the run label variable, kept
 * back as l lines, and nothing else of it. `total` is the number of bytes the kernel returned. 0
 * read to the end of what the kernel returned, else the error. */
static int scan_label(int proc, uint64_t *total)
{
    static const char digits[] = "0123456789abcdef";
    unsigned char value[LABEL_BYTES];
    int fd = open_under(proc, 0), error = 0;
    if (fd < 0)
        return errno;
    in_start(fd);
    for (;;) {
        size_t matched = 0, length = 0, index;
        int byte = in_byte();
        if (byte == -1)
            break;
        while (matched < sizeof label_name - 1 && byte == label_name[matched]) {
            matched++;
            byte = in_byte();
        }
        if (matched == sizeof label_name - 1) {
            while (byte > 0) { /* to the entry's end: its zero byte, or the end of the file */
                if (length == LABEL_BYTES) {
                    error = E2BIG;
                    break;
                }
                value[length++] = (unsigned char)byte;
                byte = in_byte();
            }
            if (error)
                break;
            if (kept_len + 4 + 2 * length > sizeof kept) {
                error = ENOMEM;
                break;
            }
            memcpy(kept + kept_len, "l =", 3);
            kept_len += 3;
            for (index = 0; index < length; index++) {
                kept[kept_len++] = digits[value[index] >> 4];
                kept[kept_len++] = digits[value[index] & 15];
            }
            kept[kept_len++] = '\n';
        } else {
            while (byte > 0) /* another variable: passed over, nothing of it kept */
                byte = in_byte();
        }
        if (byte == -1)
            break;
    }
    if (!error && in.error > 0)
        error = in.error;
    syscall(SYS_close, fd);
    *total = in.total;
    explicit_bzero(in.bytes, sizeof in.bytes);
    explicit_bzero(value, sizeof value);
    in.at = in.length = 0;
    return error;
}

/* What a task is at one moment: its start time, the two ends of its environment, its program. */
struct identity {
    uint64_t start, bounds[2], device, inode;
};

static int identify(int proc, uint64_t pid, uint64_t tid, struct identity *is)
{
    struct stat found;
    uint64_t flags;
    int error;
    path_task(pid, tid, "/stat", -1);
    error = read_stat(proc, &is->start, &flags, is->bounds);
    if (error)
        return error;
    path_task(pid, tid, "/exe", -1);
    error = stat_under(proc, &found);
    if (error)
        return error;
    is->device = found.st_dev;
    is->inode = found.st_ino;
    return 0;
}

/* The run label of one task: its l lines, written only for A WHOLE READ (above). A read that is
 * not whole is made once more. 0 written, else the error: the fact is unread, and no l line of
 * either read is written. */
static int read_label(int proc, uint64_t pid, uint64_t tid)
{
    int attempt, error = 0;
    for (attempt = 0; attempt < 2; attempt++) {
        struct identity before, after;
        uint64_t total = 0;
        kept_len = 0;
        error = identify(proc, pid, tid, &before);
        if (!error) {
            path_task(pid, tid, "/environ", -1);
            error = scan_label(proc, &total);
        }
        if (!error)
            error = identify(proc, pid, tid, &after);
        if (gone(error))
            break; /* the task has ended: it carries nothing */
        if (!error && (before.start != after.start || before.device != after.device
                       || before.inode != after.inode || before.bounds[0] != after.bounds[0]
                       || before.bounds[1] != after.bounds[1]))
            error = EAGAIN; /* it became another program while it was read */
        if (!error && total == 0)
            error = EAGAIN; /* nothing returned: what the kernel says of a task that is executing */
        if (!error && total != before.bounds[1] - before.bounds[0])
            error = EAGAIN; /* the read ended before the environment did */
        if (!error)
            break;
    }
    if (!error) {
        if (kept_len)
            put(kept, kept_len);
        else {
            word("l -");
            finish();
        }
    }
    explicit_bzero(kept, sizeof kept);
    kept_len = 0;
    return error;
}

struct task {
    int proc;
    uint64_t pid, tid;
    int failed; /* the first error of the task's descriptors */
};

static void descriptor(uint64_t fd, void *with)
{
    struct task *task = with;
    uint64_t mount = 0, inode = 0, major = 0, minor = 0;
    int error, known, added;
    path_task(task->pid, task->tid, "/fdinfo/", (int64_t)fd);
    error = read_fdinfo(task->proc, &mount, &inode);
    if (error) {
        if (!gone(error) && !task->failed) /* gone: closed meanwhile */
            task->failed = error;
        return;
    }
    known = mount_find(mount, &major, &minor);
    added = add('f', fd, mount, known ? ((major << 32) | minor) + 1 : 0, inode, 1);
    if (added < 0) {
        if (!task->failed)
            task->failed = ENOMEM;
        return;
    }
    if (!added)
        return;
    word("f ");
    number(fd);
    word(" ");
    number(mount);
    word(" ");
    if (known) {
        number(major);
        word(":");
        number(minor);
    } else
        word("-");
    word(" ");
    number(inode);
    finish();
}

static uint64_t tasks[TASKS];
static uint32_t task_count;
static int task_overflow;

static void task_listed(uint64_t tid, void *with)
{
    (void)with;
    if (task_count < TASKS)
        tasks[task_count++] = tid;
    else
        task_overflow = 1;
}

static void task_again(uint64_t tid, void *with)
{
    int *missed = with;
    if (add('t', tid, 0, 0, 0, 0))
        *missed = 1;
}

static int task_descriptors(struct task *task)
{
    int folder, error;
    path_task(task->pid, task->tid, "/fdinfo", -1);
    folder = open_under(task->proc, O_DIRECTORY);
    if (folder < 0)
        return errno;
    error = numbered(folder, descriptor_entries, descriptor, task);
    syscall(SYS_close, folder);
    return error;
}

/* One task: its working directory, its run label and its descriptors. */
static void read_task(int proc, uint64_t pid, uint64_t tid)
{
    struct stat found;
    struct task task = {proc, pid, tid, 0};
    int error = 0;
    add('t', tid, 0, 0, 0, 1); /* read, also when it has ended: it holds nothing then */
    path_task(pid, tid, "/cwd", -1);
    error = stat_under(proc, &found);
    if (gone(error))
        return; /* the task has ended: no line */
    word("t ");
    number(tid);
    finish();
    if (error)
        unread("cwd", error);
    else {
        uint64_t major = gnu_dev_major(found.st_dev), minor = gnu_dev_minor(found.st_dev);
        int added = add('c', major, minor, found.st_ino, 0, 1);
        if (added < 0)
            unread("cwd", ENOMEM);
        else if (added) {
            word("c ");
            number(major);
            word(":");
            number(minor);
            word(" ");
            number(found.st_ino);
            finish();
        }
    }
    error = read_label(proc, pid, tid);
    if (error && !gone(error)) /* gone: the task ended before its environment was read */
        unread("env", error);
    error = task_descriptors(&task);
    if (gone(error))
        error = 0; /* ended while it was read: what it held is closed */
    if (!error)
        error = task.failed;
    if (error)
        unread("fd", error);
}

/* maps: START-END PERMS OFFSET MAJOR:MINOR INODE [PATH], the device in hexadecimal. */
static int read_maps(int proc, uint64_t pid)
{
    int fd, error = 0;
    path_start(pid, "/maps");
    fd = open_under(proc, 0);
    if (fd < 0)
        return errno;
    in_start(fd);
    held = -2;
    for (;;) {
        uint64_t major, minor, inode;
        int added;
        if (skip_blanks() == -1)
            break;
        skip_word(); /* the addresses */
        skip_blanks();
        skip_word(); /* the permissions */
        skip_blanks();
        skip_word(); /* the offset */
        skip_blanks();
        if (!read_number(16, &major) || next() != ':' || !read_number(16, &minor) || next() != ' '
            || !read_number(10, &inode)) {
            error = EINVAL;
            break;
        }
        skip_line();
        if (!inode)
            continue;
        added = add('m', major, minor, inode, 0, 1);
        if (added == 0)
            continue;
        word("m ");
        number(major);
        word(":");
        number(minor);
        word(" ");
        number(inode);
        finish(); /* a full table only repeats a pair, which the format allows */
    }
    if (!error && in.error > 0)
        error = in.error;
    syscall(SYS_close, fd);
    return error;
}

static uint64_t blocks;

static void process(uint64_t pid, void *with)
{
    int proc = *(int *)with, error, folder, missed = 0;
    uint64_t start = 0, flags = 0;
    uint32_t index;

    path_start(pid, "/stat");
    error = read_stat(proc, &start, &flags, NULL);
    if (gone(error))
        return; /* ended before it was read: no block */
    if (!error && (flags & KERNEL_THREAD))
        return;
    stamp++;
    used = mounts_used = 0;
    task_count = 0;
    task_overflow = 0;
    blocks++;
    word("p ");
    number(pid);
    word(" ");
    number(start);
    finish();
    if (error) {
        unread("stat", error);
        return;
    }
    error = read_mounts(proc, pid);
    if (gone(error))
        goto ended;
    if (error)
        unread("mnt", error);

    path_start(pid, "/task");
    folder = open_under(proc, O_DIRECTORY);
    if (folder < 0) {
        if (gone(errno))
            goto ended;
        unread("task", errno);
    } else {
        error = numbered(folder, task_entries, task_listed, NULL);
        syscall(SYS_close, folder);
        if (gone(error))
            goto ended;
        if (error || task_overflow)
            unread("task", error ? error : ENOMEM);
        for (index = 0; index < task_count; index++)
            read_task(proc, pid, tasks[index]);
        /* The second listing: a task that is there now and was not read is an unread fact. */
        path_start(pid, "/task");
        folder = open_under(proc, O_DIRECTORY);
        if (folder < 0) {
            if (gone(errno))
                goto ended;
            unread("task", errno);
        } else {
            error = numbered(folder, task_entries, task_again, &missed);
            syscall(SYS_close, folder);
            if (gone(error))
                goto ended;
            if (error)
                unread("task", error);
            else if (missed)
                unread("task", 0);
        }
    }
    error = read_maps(proc, pid);
    if (gone(error))
        goto ended;
    if (error)
        unread("maps", error);
    return;
ended:
    word("g");
    finish();
}

static int holds_capability(void)
{
    struct __user_cap_header_struct header = {_LINUX_CAPABILITY_VERSION_3, 0};
    struct __user_cap_data_struct data[2];
    memset(data, 0, sizeof data);
    if (syscall(SYS_capget, &header, data) < 0)
        return 0;
    return (data[0].effective >> PTRACE_CAPABILITY) & 1;
}

/* no_new_privs and the filter: from here the kernel ends the process on any other call. */
static void lock_in(void)
{
    struct sock_fprog program = {sizeof filter / sizeof filter[0], filter};
    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0)
        _exit(5);
    if (prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &program) != 0)
        _exit(5);
}

int main(int argc, char **argv)
{
    struct statfs what;
    char byte;
    int proc, capable, error;
    (void)argv;
    if (argc > 1)
        return 2;
    capable = holds_capability();
    signal(SIGPIPE, SIG_IGN);
    lock_in();

    proc = (int)syscall(SYS_openat, AT_FDCWD, "/proc", O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (proc < 0 || syscall(SYS_fstatfs, proc, &what) < 0 || (long)what.f_type != PROC_MAGIC)
        leave(4);

    word("veldo-procread 1 cap=");
    number((uint64_t)capable);
    finish();
    flush();
    /* The table is read only after this read has returned, whatever it returned. */
    syscall(SYS_read, 1, &byte, 1);

    error = numbered(proc, table_entries, process, &proc);
    if (error)
        leave(3); /* the table itself could not be listed: no end line */
    flush();
    word("end ");
    number(blocks);
    finish();
    flush();
    /* Stay until the probe has looked: it shuts down its side after its last look. */
    syscall(SYS_read, 1, &byte, 1);
    leave(0);
    return 0;
}
