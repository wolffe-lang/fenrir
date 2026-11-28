/* Linked musl witness for the documented one-byte list boundary. */
typedef long Word;
extern void __wolf_rt_main_start(int argc, char **argv, char **envp);
extern Word __wolf_rt_list_new(Word size);
extern void __wolf_rt_list_push(Word list, const void *element);
extern Word __wolf_rt_list_read(Word list, Word index, void *out);
extern Word __wolf_rt_list_write(Word list, Word index, const void *element);
extern Word __wolf_rt_list_pop(Word list, void *out);
extern Word __wolf_rt_list_slice(Word list, Word low, Word high);
extern Word __wolf_rt_list_len(Word list);
extern void __wolf_rt_list_clear(Word list);
extern void __wolf_rt_list_reserve(Word list, Word capacity);
extern void __wolf_rt_print_str(const char *bytes, Word length);

int main(int argc, char **argv, char **envp) {
    __wolf_rt_main_start(argc, argv, envp);
    const Word values[4] = {0, 127, 128, 255};
    Word list = __wolf_rt_list_new(1);
    for (Word i = 0; i < 4; ++i) __wolf_rt_list_push(list, &values[i]);
    if (__wolf_rt_list_len(list) != 4) return 10;
    for (Word i = 0; i < 4; ++i) {
        Word out = 0;
        if (__wolf_rt_list_read(list, i, &out) != 1 || out != values[i]) return 11;
    }
    Word sentinel = 0x01020304050607A5L;
    if (__wolf_rt_list_read(list, 3, &sentinel) != 1 || sentinel != 0x01020304050607FFL) return 12;
    Word slice = __wolf_rt_list_slice(list, 1, 4);
    if (__wolf_rt_list_len(slice) != 3) return 13;
    Word value = 128;
    if (__wolf_rt_list_write(list, 0, &value) != 1) return 14;
    value = 0;
    if (__wolf_rt_list_read(list, 0, &value) != 1 || value != 128) return 15;
    value = 0;
    if (__wolf_rt_list_pop(slice, &value) != 1 || value != 255) return 16;
    __wolf_rt_list_clear(list);
    if (__wolf_rt_list_len(list) != 0 || __wolf_rt_list_len(slice) != 2) return 17;
    value = 0x01020304050607A5L;
    if (__wolf_rt_list_read(list, 0, &value) != 0 || value != 0x01020304050607A5L) return 18;
    __wolf_rt_list_reserve(list, 256);
    value = 255;
    __wolf_rt_list_push(list, &value);
    value = 0;
    if (__wolf_rt_list_read(list, 0, &value) != 1 || value != 255) return 19;
    __wolf_rt_print_str("byte-runtime-ok\n", 16);
    return 0;
}
