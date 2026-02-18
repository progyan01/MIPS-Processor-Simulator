import sys

#Constants
TEXT_START = 0x00400000
DATA_START = 0x10010000

class RegisterFile:
    def __init__(self):
        self.regs = [0] * 32
    
    def read(self, reg_num):
        return self.regs[reg_num]
    
    def write(self, reg_num, value):
        if reg_num != 0: # $zero is always 0
            self.regs[reg_num] = value & 0xFFFFFFFF # Keep it 32-bit
            
    def dump(self):
        print(f"\n[Register Dump]")
        for i in range(0, 32, 4):
            print(f"R{i:02d}-R{i+3:02d}: {self.regs[i:i+4]}")

class ALU:
    def execute(self, alu_op, operand1, operand2, shamt=0):
        res = 0
        if alu_op == 'ADD':  res = operand1 + operand2
        elif alu_op == 'SUB': res = operand1 - operand2
        elif alu_op == 'AND': res = operand1 & operand2
        elif alu_op == 'OR':  res = operand1 | operand2
        elif alu_op == 'SLT': res = 1 if operand1 < operand2 else 0
        elif alu_op == 'SLL': res = operand2 << shamt
        elif alu_op == 'SRL': res = operand2 >> shamt
        elif alu_op == 'LUI': res = operand2 << 16
        return res & 0xFFFFFFFF # Enforce 32-bit wrap-around

class Memory:
    def __init__(self):
        self.data = {} # Dictionary maps Address -> Byte

    def load_word(self, address):
        # Little-endian load (standard for MARS/MIPS simulators)
        b0 = self.data.get(address, 0)
        b1 = self.data.get(address+1, 0)
        b2 = self.data.get(address+2, 0)
        b3 = self.data.get(address+3, 0)
        return (b0) | (b1 << 8) | (b2 << 16) | (b3 << 24)

    def store_word(self, address, value):
        self.data[address]   = value & 0xFF
        self.data[address+1] = (value >> 8) & 0xFF
        self.data[address+2] = (value >> 16) & 0xFF
        self.data[address+3] = (value >> 24) & 0xFF
        
    def load_string(self, address):
        chars = []
        while True:
            char = self.data.get(address, 0)
            if char == 0: break
            chars.append(chr(char))
            address += 1
        return "".join(chars)

class MIPS_Processor:
    def __init__(self):
        self.pc = TEXT_START
        self.reg_file = RegisterFile()
        self.alu = ALU()
        self.memory = Memory()
        self.running = True

    def load_segments(self, text_file, data_file):
        # Load Instructions (Text Segment)
        current_addr = TEXT_START
        try:
            with open(text_file, 'r') as f:
                for line in f:
                    # Parse Binary Text ("0010...") to int
                    inst = int(line.strip(), 2) 
                    self.memory.store_word(current_addr, inst)
                    current_addr += 4
        except FileNotFoundError:
            print(f"Error: {text_file} not found.")

        # Load Data (Data Segment)
        current_addr = DATA_START
        try:
            with open(data_file, 'r') as f:
                for line in f:
                    val = int(line.strip(), 2)
                    self.memory.store_word(current_addr, val)
                    current_addr += 4
        except FileNotFoundError:
            print(f"Warning: {data_file} not found (Data segment empty).")

    def run(self):
        print("--- Simulation Start ---")
        while self.running:
            # 1. IF: Instruction Fetch
            instruction = self.memory.load_word(self.pc)
            next_pc = self.pc + 4

            if instruction == 0: # NOP or end of code
                print("End of instructions.")
                break

            # 2. ID: Instruction Decode
            opcode = (instruction >> 26) & 0x3F
            rs = (instruction >> 21) & 0x1F
            rt = (instruction >> 16) & 0x1F
            rd = (instruction >> 11) & 0x1F
            shamt = (instruction >> 6) & 0x1F
            funct = instruction & 0x3F
            imm = instruction & 0xFFFF
            
            # Sign Extend Immediate
            imm_se = imm if (imm < 0x8000) else imm - 0x10000

            # Control Signals (Simplified)
            alu_op = None
            mem_read = False
            mem_write = False
            reg_write = False
            branch = False
            jump = False
            
            # 3. EX: Execute & Control Logic
            target_reg = rd # Default for R-type
            
            # R-Type Instructions
            if opcode == 0:
                reg_write = True
                if funct == 32: alu_op = 'ADD'
                elif funct == 34: alu_op = 'SUB'
                elif funct == 36: alu_op = 'AND'
                elif funct == 37: alu_op = 'OR'
                elif funct == 42: alu_op = 'SLT'
                elif funct == 0:  alu_op = 'SLL'
                elif funct == 2:  alu_op = 'SRL'
                elif funct == 12: # SYSCALL
                    self.handle_syscall()
                    reg_write = False # Syscall doesn't use WB stage
            
            # I-Type Instructions
            elif opcode == 8:  alu_op = 'ADD'; target_reg = rt; reg_write = True # ADDI
            elif opcode == 9:  alu_op = 'ADD'; target_reg = rt; reg_write = True # ADDIU
            elif opcode == 12: alu_op = 'AND'; target_reg = rt; reg_write = True # ANDI
            elif opcode == 13: alu_op = 'OR';  target_reg = rt; reg_write = True # ORI
            elif opcode == 15: alu_op = 'LUI'; target_reg = rt; reg_write = True # LUI
            elif opcode == 35: alu_op = 'ADD'; target_reg = rt; reg_write = True; mem_read = True # LW
            elif opcode == 43: alu_op = 'ADD'; mem_write = True # SW
            elif opcode == 4:  branch = True # BEQ
            elif opcode == 5:  branch = True # BNE
            
            # J-Type Instructions
            elif opcode == 2: jump = True # J

            # Execute ALU
            val1 = self.reg_file.read(rs)
            val2 = self.reg_file.read(rt)
            
            # Select ALU Operand 2 (Immediate or Register)
            alu_in2 = imm_se if (opcode != 0 and opcode != 4 and opcode != 5) else val2
            
            alu_result = 0
            if alu_op:
                alu_result = self.alu.execute(alu_op, val1, alu_in2, shamt)

            # Branch/Jump Logic
            if jump:
                # Jump target: top 4 bits of PC + 26 bits of inst shifted left 2
                next_pc = (next_pc & 0xF0000000) | ((instruction & 0x03FFFFFF) << 2)
            elif branch:
                taken = False
                if opcode == 4 and val1 == val2: taken = True    # BEQ
                if opcode == 5 and val1 != val2: taken = True    # BNE
                if taken:
                    next_pc = next_pc + (imm_se << 2)

            # 4. MEM: Memory Access
            mem_data = 0
            if mem_read:
                mem_data = self.memory.load_word(alu_result)
            elif mem_write:
                self.memory.store_word(alu_result, val2)

            # 5. WB: Write Back
            if reg_write:
                # If loading from memory, write mem_data, else write ALU result
                write_val = mem_data if mem_read else alu_result
                self.reg_file.write(target_reg, write_val)

            # Advance PC
            self.pc = next_pc
        
        self.reg_file.dump()

    def handle_syscall(self):
        v0 = self.reg_file.read(2) # $v0
