/* fn10, tests/memory/maxrss.c: a small parent for one measured child (docs/MEMORY.md 7).
 *
 *   maxrss REPORT PROGRAM [ARG...]
 *
 * Runs PROGRAM with its standard streams inherited, reaps it with wait4, writes its ru_maxrss in KiB to REPORT
 * (Linux counts KiB, macOS bytes), and exits with the child's status (128 + the signal for a signalled child).
 * ru_maxrss survives exec, so a child forked from a large parent reports at least the parent's resident set;
 * this parent is a few hundred KiB, so the child's peak is its own.
 */
#include <stdio.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: maxrss REPORT PROGRAM [ARG...]\n");
        return 2;
    }
    pid_t pid = fork();
    if (pid < 0) {
        perror("maxrss: fork");
        return 2;
    }
    if (pid == 0) {
        execv(argv[2], argv + 2);
        perror("maxrss: exec");
        _exit(127);
    }
    int status = 0;
    struct rusage usage;
    if (wait4(pid, &status, 0, &usage) != pid) {
        perror("maxrss: wait4");
        return 2;
    }
    FILE *report = fopen(argv[1], "w");
    if (report == NULL) {
        perror("maxrss: report");
        return 2;
    }
#ifdef __APPLE__
    fprintf(report, "%ld\n", (long)usage.ru_maxrss / 1024);
#else
    fprintf(report, "%ld\n", (long)usage.ru_maxrss);
#endif
    fclose(report);
    if (WIFSIGNALED(status)) return 128 + WTERMSIG(status);
    return WEXITSTATUS(status);
}
