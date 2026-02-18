.data
    # Use a sorted array to test lower_bound
    array:  .word 1, 3, 5, 7, 9, 11, 13, 15
    size:   .word 8             # Length of the array
    target: .word 6             # We want to find the first element >= 6
    result: .word -1            # Memory location to store the final answer (SW requirement)
    
    # Strings for printing to console
    msg:    .asciiz "Lower Bound Index: "

.text
.globl main

main:
    # Setup & Load Variables
    la      $s0, array          # $s0 = Base address of array
    lw      $s1, size           # $s1 = high (initially size n)
    lw      $s2, target         # $s2 = target value
    li      $t0, 0              # $t0 = low (initially 0)
    
    move    $t4, $s1            # $t4 = ans (initially n, in case all elements < target)

    # Binary Search Loop
loop:
    bge     $t0, $s1, end_loop  # while (low < high) { ... }
    
    # Calculate mid = low + (high - low) / 2
    sub     $t1, $s1, $t0       # $t1 = high - low
    srl     $t1, $t1, 1         # $t1 = (high - low) / 2 (Shift Right Logical)
    add     $t1, $t1, $t0       # $t1 = mid = low + offset

    # Calculate address of array[mid]
    sll     $t2, $t1, 2         # offset = mid * 4 bytes
    add     $t2, $s0, $t2       # address = base + offset
    
    # Load array[mid]
    lw      $t3, 0($t2)         # $t3 = array[mid]

    # Compare array[mid] with target
    blt     $t3, $s2, go_right  # if (array[mid] < target) -> go right

    # Left Half Logic (array[mid] >= target)
    move    $t4, $t1            # ans = mid (potential candidate)
    move    $s1, $t1            # high = mid
    j       loop                # continue loop

    # Right Half Logic (array[mid] < target)
go_right:
    addi    $t0, $t1, 1         # low = mid + 1
    j       loop                # continue loop

end_loop:
    # Store Result
    sw      $t4, result         # Write the final index back to memory
    
    # Print Result
    li      $v0, 4              # syscall: print_string
    la      $a0, msg
    syscall

    li      $v0, 1              # syscall: print_int
    move    $a0, $t4            # Print the index stored in $t4
    syscall

    # Exit program
    li      $v0, 10
    syscall
