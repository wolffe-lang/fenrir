.text
.globl main
.type main, @function
main:
pushq %rbp
movq %rsp, %rbp
subq $16, %rsp
call __wolf_rt_main_start
leaq -8(%rbp), %rdi
leaq -16(%rbp), %rsi
call __fenrir_f0
movl -8(%rbp), %eax
movq %rbp, %rsp
popq %rbp
ret
.size main, .-main
.globl __fenrir_f0
.type __fenrir_f0, @function
__fenrir_f0:
pushq %rbp
movq %rsp, %rbp
subq $32, %rsp
movq %rdi, -8(%rbp)
.Lf0_b0:
leaq -16(%rbp), %rdi
leaq -24(%rbp), %rsi
call __fenrir_f1
movabsq $0, %rax
movq %rax, -24(%rbp)
movq -8(%rbp), %rdi
movq -24(%rbp), %rax
movq %rax, 0(%rdi)
movq %rbp, %rsp
popq %rbp
ret
.size __fenrir_f0, .-__fenrir_f0
.globl __fenrir_f1
.type __fenrir_f1, @function
__fenrir_f1:
pushq %rbp
movq %rsp, %rbp
subq $240, %rsp
movq %rdi, -8(%rbp)
.Lf1_b0:
movabsq $0, %rax
movq %rax, -24(%rbp)
movq -24(%rbp), %rax
movq %rax, -216(%rbp)
movabsq $0, %rax
movq %rax, -32(%rbp)
movq -32(%rbp), %rax
movq %rax, -224(%rbp)
jmp .Lf1_b1
.Lf1_b1:
movq -216(%rbp), %rax
movq %rax, -40(%rbp)
movabsq $4, %rax
movq %rax, -48(%rbp)
movq -40(%rbp), %rax
movq -48(%rbp), %rcx
cmpq %rcx, %rax
setl %al
movzbq %al, %rax
movq %rax, -56(%rbp)
movq -56(%rbp), %rax
cmpq $0, %rax
je .Lf1_b1_i3_false
jmp .Lf1_b2
.Lf1_b1_i3_false:
jmp .Lf1_b3
.Lf1_b2:
movabsq $0, %rax
movq %rax, -64(%rbp)
movq -64(%rbp), %rax
movq %rax, -232(%rbp)
jmp .Lf1_b4
.Lf1_b3:
movq -224(%rbp), %rax
movq %rax, -72(%rbp)
call __wolf_rt_strbuf_new
movq %rax, -16(%rbp)
movq -16(%rbp), %rdi
movq -72(%rbp), %rsi
movq $0, %rdx
call __wolf_rt_strbuf_i64
movq -16(%rbp), %rdi
leaq -88(%rbp), %rsi
call __wolf_rt_strbuf_finish
movq -88(%rbp), %rdi
movq -80(%rbp), %rsi
call __wolf_rt_print_str
leaq .Lnewline(%rip), %rdi
movq $1, %rsi
call __wolf_rt_print_str
movq %rbp, %rsp
popq %rbp
ret
.Lf1_b4:
movq -232(%rbp), %rax
movq %rax, -96(%rbp)
movabsq $4, %rax
movq %rax, -104(%rbp)
movq -96(%rbp), %rax
movq -104(%rbp), %rcx
cmpq %rcx, %rax
setl %al
movzbq %al, %rax
movq %rax, -112(%rbp)
movq -112(%rbp), %rax
cmpq $0, %rax
je .Lf1_b4_i3_false
jmp .Lf1_b5
.Lf1_b4_i3_false:
jmp .Lf1_b6
.Lf1_b5:
movq -232(%rbp), %rax
movq %rax, -120(%rbp)
movq -216(%rbp), %rax
movq %rax, -128(%rbp)
movq -120(%rbp), %rax
movq -128(%rbp), %rcx
cmpq %rcx, %rax
sete %al
movzbq %al, %rax
movq %rax, -136(%rbp)
movq -136(%rbp), %rax
cmpq $0, %rax
je .Lf1_b5_i3_false
jmp .Lf1_b7
.Lf1_b5_i3_false:
jmp .Lf1_b8
.Lf1_b6:
movq -216(%rbp), %rax
movq %rax, -144(%rbp)
movabsq $1, %rax
movq %rax, -152(%rbp)
movq -144(%rbp), %rax
movq -152(%rbp), %rcx
addl %ecx, %eax
jno .Lf1_b6_i2_ok
movl $1, %edi
leaq .Lblob0(%rip), %rsi
movq $57, %rdx
movabsq $7, %rcx
movabsq $9, %r8
call __wolf_rt_trap_at
ud2
.Lf1_b6_i2_ok:
movslq %eax, %rax
movq %rax, -160(%rbp)
movq -160(%rbp), %rax
movq %rax, -216(%rbp)
jmp .Lf1_b1
.Lf1_b7:
jmp .Lf1_b6
.Lf1_b8:
movq -224(%rbp), %rax
movq %rax, -168(%rbp)
movabsq $1, %rax
movq %rax, -176(%rbp)
movq -168(%rbp), %rax
movq -176(%rbp), %rcx
addl %ecx, %eax
jno .Lf1_b8_i2_ok
movl $1, %edi
leaq .Lblob0(%rip), %rsi
movq $57, %rdx
movabsq $6, %rcx
movabsq $44, %r8
call __wolf_rt_trap_at
ud2
.Lf1_b8_i2_ok:
movslq %eax, %rax
movq %rax, -184(%rbp)
movq -184(%rbp), %rax
movq %rax, -224(%rbp)
movq -232(%rbp), %rax
movq %rax, -192(%rbp)
movabsq $1, %rax
movq %rax, -200(%rbp)
movq -192(%rbp), %rax
movq -200(%rbp), %rcx
addl %ecx, %eax
jno .Lf1_b8_i6_ok
movl $1, %edi
leaq .Lblob0(%rip), %rsi
movq $57, %rdx
movabsq $6, %rcx
movabsq $56, %r8
call __wolf_rt_trap_at
ud2
.Lf1_b8_i6_ok:
movslq %eax, %rax
movq %rax, -208(%rbp)
movq -208(%rbp), %rax
movq %rax, -232(%rbp)
jmp .Lf1_b4
.size __fenrir_f1, .-__fenrir_f1
.section .rodata
.Lnewline:
.byte 10
.Lblob0:
.byte 47
.byte 115
.byte 114
.byte 118
.byte 47
.byte 98
.byte 117
.byte 105
.byte 108
.byte 100
.byte 47
.byte 102
.byte 101
.byte 110
.byte 114
.byte 105
.byte 114
.byte 47
.byte 116
.byte 101
.byte 115
.byte 116
.byte 115
.byte 47
.byte 99
.byte 111
.byte 109
.byte 112
.byte 105
.byte 108
.byte 101
.byte 47
.byte 101
.byte 45
.byte 114
.byte 101
.byte 100
.byte 47
.byte 110
.byte 101
.byte 115
.byte 116
.byte 101
.byte 100
.byte 45
.byte 108
.byte 111
.byte 111
.byte 112
.byte 47
.byte 109
.byte 97
.byte 105
.byte 110
.byte 46
.byte 108
.byte 117
.section .note.GNU-stack,"",@progbits
