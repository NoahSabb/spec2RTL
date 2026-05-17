
import cocotb
from cocotb.triggers import FallingEdge, RisingEdge, ReadOnly, NextTimeStep, Timer
import random

async def dut_init(dut):
    # iterate all the input signals and initialize with 0
    for signal in dut:
        try:
            signal.value = 0
        except Exception:
            pass

async def reset_dut(reset, duration_ns = 10):
    # Restart Interface
    reset.value = 1
    await Timer(duration_ns, unit="ns")
    reset.value = 0
    await Timer(duration_ns, unit="ns")
    reset.value = 1
    await Timer(duration_ns, unit='ns')
    reset._log.debug("Reset complete")



class DataMemory:
    def __init__(self):
        self.mem_array = [0] * (2**8)  # 32-bit memory addresses

    # Value tuple is a tuple (addr, we, be, wdata)
    def write_addr(self, value):
        """
        Perform a memory write operation considering the byte enable (BE).
        """
        addr, we, be, wdata = value

        if we:  # Write enable is asserted
            current_word = self.mem_array[addr]
            for byte_index in range(4):
                if be & (1 << byte_index):  
                    current_word &= ~(0xFF << (byte_index * 8))
                    current_word |= (wdata & (0xFF << (byte_index * 8)))

            self.mem_array[addr] = current_word

    def read_addr(self, value):
        """
        Perform a memory read operation considering the byte enable (BE).
        """
        addr, _, be, _ = value

        
        current_word = self.mem_array[addr]

        
        read_data = 0
        for byte_index in range(4):
            if be & (1 << byte_index):  
                read_data |= (current_word & (0xFF << (byte_index * 8)))

        return read_data

class ExReqDriver:
    def __init__(self, dut, name, clk, sb_callback):
        """
        Initialize the InputDriver.
        :param dut: The DUT instance.
        :param name: The name of the bus signals (e.g., 'input_bus').
        :param clk: Clock signal for synchronization.
        :param sb_callback: Callback function to handle data/address events.
        """
        self.dut = dut
        self.clk = clk
        self.callback = sb_callback

        # Initialize bus signals
        self.bus = {
            "req_i"         : getattr(dut, f"{name}_req_i"),
            "we_i"          : getattr(dut, f"{name}_we_i"),
            "type_i"        : getattr(dut, f"{name}_type_i"),
            "wdata_i"       : getattr(dut, f"{name}_wdata_i"),
            "addr_base_i"   : getattr(dut, f"{name}_addr_base_i"),
            "addr_offset_i" : getattr(dut, f"{name}_addr_offset_i"),
            "ready_o"       : getattr(dut, f"{name}_ready_o"),    
        }

        # Reset bus values
        self.bus["req_i"].value = 0

    async def write_req(self, value):
        """
        Send a value over the bus.
        :param value: A tuple (type, wdata, base_addr, off_addr) to send on the bus.
        """
        # Random delay before request
        for _ in range(random.randint(1, 20)):
            await RisingEdge(self.clk)

        # Wait until ready signal is asserted
        # PROMPT: " ex_if_req_i Should only be asserted if the module is ready"
        while self.bus["ready_o"].value != 1:
            await RisingEdge(self.clk)

        # Drive the bus
        # PROMPT:
        # The module will register the calculated 
        # address, write data (if applicable), and control signals (e.g., write enable, byte enable) to signal a data memory request.
        self.bus["req_i"].value = 1
        self.bus["we_i"].value = 1
        self.bus["type_i"].value = value[0]
        self.bus["wdata_i"].value = value[1]
        self.bus["addr_base_i"].value = value[2]
        self.bus["addr_offset_i"].value = value[3]


        # Allow ReadOnly phase and trigger the callback
        await ReadOnly()
        self.callback(self.dut, int(self.bus["type_i"].value), int(self.bus["wdata_i"].value), int(self.bus["addr_base_i"].value), int(self.bus["addr_offset_i"].value))

        # Hold the enable signal for one clock cycle
        await RisingEdge(self.clk)
        self.bus["req_i"].value = 0
        self.bus["we_i"].value = 0

        # The request is forwarded to dmem IFF it's aligned
        type = value[0] 
        address = (value[2]+ value[3])
        if type == 0x0:
            trans_size = 1
        elif type == 0x1:
            trans_size = 2
        elif type == 0x2:
            trans_size = 4
        aligned =  (address % trans_size) == 0

        # Add a delay to simulate bus deactivation
        await NextTimeStep()
        dut_req = int(self.dut.dmem_req_o.value)
        dut_address = int(self.dut.dmem_req_addr_o.value)
        dut_we = int(self.dut.dmem_req_we_o.value)
        dut_be = int(self.dut.dmem_req_be_o.value)
        dut_wdata = int(self.dut.dmem_req_wdata_o.value)
        # DMEM REQUEST IS FORWARDED
        if aligned:
            assert dut_req == 1, f"Dmem request should be asserted"
            assert dut_address == address, f"Dmem address mismatch: Expected:{address}, Got:{dut_address}"
            assert dut_we == 1, f"Dmem we mismatch: Expected: 1, Got:{dut_we}"
            assert dut_wdata == value[1], f"Dmem address mismatch: Expected:{value[1]}, Got:{dut_wdata}"
            # PROMPT: `ex_if_ready_o` is deasserted sequentially indicating an outstanding access.
            assert self.bus["ready_o"].value == 0, f"ready should deasserted sequentially"
        else:
            assert dut_req == 0, f"Dmem request should be deasserted"

    async def read_req(self, value):
        """
        Send a value over the bus.
        :param value: A tuple (type, wdata, base_addr, off_addr) to send on the bus.
        """
        # Random delay before sending data
        #PROMPT: " ex_if_req_i Should only be asserted if the module is ready"
        for _ in range(random.randint(1, 20)):
            await RisingEdge(self.clk)

        # Wait until ready signal is asserted
        # PROMPT: " ex_if_req_i Should only be asserted if the module is ready"
        while self.bus["ready_o"].value != 1:
            await RisingEdge(self.clk)

        # Drive the bus
        # PROMPT:
        # The module will register the calculated 
        # address, write data (if applicable), and control signals (e.g., write enable, byte enable) to signal a data memory request.
        self.bus["req_i"].value = 1
        self.bus["we_i"].value = 0
        self.bus["type_i"].value = value[0]
        self.bus["wdata_i"].value = 0
        self.bus["addr_base_i"].value = value[2]
        self.bus["addr_offset_i"].value = value[3]


        # Allow ReadOnly phase and trigger the callback
        await ReadOnly()
        self.callback(self.dut, int(self.bus["type_i"].value), int(self.bus["wdata_i"].value), int(self.bus["addr_base_i"].value), int(self.bus["addr_offset_i"].value))

        # Hold the enable signal for one clock cycle
        await RisingEdge(self.clk)
        self.bus["req_i"].value = 0

        # The request is forwarded to dmem IFF it's aligned
        type = value[0] 
        address = (value[2]+ value[3])
        if type == 0x0:
            trans_size = 1
        elif type == 0x1:
            trans_size = 2
        elif type == 0x2:
            trans_size = 4
        aligned =  (address % trans_size) == 0

        # Add a delay to simulate bus deactivation
        await NextTimeStep()
        dut_req = int(self.dut.dmem_req_o.value)
        dut_address = int(self.dut.dmem_req_addr_o.value)
        dut_we = int(self.dut.dmem_req_we_o.value)
        dut_be = int(self.dut.dmem_req_be_o.value)
        if aligned:
            assert dut_req == 1, f"Dmem request should be asserted"
            assert dut_address == address, f"Dmem address mismatch: Expected:{address}, Got:{dut_address}"
            assert dut_we == 0, f"Dmem we mismatch: Expected: 1, Got:{dut_we}"
            # PROMPT: `ex_if_ready_o` is deasserted sequentially indicating an outstanding access.
            assert self.bus["ready_o"].value == 0, f"ready should deasserted sequentially"
        else:
            assert dut_req == 0, f"Dmem request should be deasserted"



class dmemIFDriver:
    def __init__(self, dut, name, clk):
        """
        Initialize the InputDriver.
        :param dut: The DUT instance.
        :param name: The name of the bus signals (e.g., 'input_bus').
        :param clk: Clock signal for synchronization.
        """
        self.dut = dut
        self.clk = clk
        # Initialize bus signals
        self.bus = {
            "req_o"        : getattr(dut, f"{name}_req_o"),
            "req_addr_o"   : getattr(dut, f"{name}_req_addr_o"),
            "req_we_o"     : getattr(dut, f"{name}_req_we_o"),
            "req_be_o"     : getattr(dut, f"{name}_req_be_o"),
            "req_wdata_o"  : getattr(dut, f"{name}_req_wdata_o"),
            "rsp_rdata_i"  : getattr(dut, f"{name}_rsp_rdata_i"),
            "rvalid_i"     : getattr(dut, f"{name}_rvalid_i"),
            "gnt_i"        : getattr(dut, f"{name}_gnt_i"),    
        }

        # Reset bus values
        self.bus["rvalid_i"].value = 0
        self.bus["rsp_rdata_i"].value = 0
        self.bus["gnt_i"].value = 0
        self.dmem_model = DataMemory()
        cocotb.start_soon(self._listening())


    async def _listening(self):
        while True:
            while self.bus["req_o"].value != 1:
                await RisingEdge(self.clk)
            addr = int(self.bus["req_addr_o"].value)
            we = int(self.bus["req_we_o"].value)
            be = int(self.bus["req_be_o"].value)
            wdata = int(self.bus["req_wdata_o"].value)
            Req_vector = (addr, we, be, wdata)
            await self._process_req(Req_vector)
            
          
    async def _process_req(self, value):
        """
        Send a value over the bus.
        :param value: A tuple (addr, we, be, wdata) to send on the bus.
        """
        wb_check = False
        # Wait random time to gnt the request 
        for _ in range(random.randint(1, 5)):
            await RisingEdge(self.clk)
        self.bus["gnt_i"].value = 1
        await RisingEdge(self.clk)
        self.bus["gnt_i"].value = 0
        await ReadOnly()
        #PROMPT: `dmem_req_o` is cleared sequentially after data memory accepts the request.
        assert int(self.dut.dmem_req_o.value) ==0, f'dmem_req_o must be deasserted'
        if value[1] == 1: #Write req
            self.dmem_model.write_addr(value)
            await RisingEdge(self.clk)
        else: #Read req
           # Read from mem model
           rdata = self.dmem_model.read_addr(value)
           wb_check = True 
           for _ in range(random.randint(1, 5)):
               await RisingEdge(self.clk) 
           self.bus["rvalid_i"].value = 1
           self.bus["rsp_rdata_i"].value = rdata 
           await RisingEdge(self.clk)
           self.bus["rvalid_i"].value = 0
           self.bus["rsp_rdata_i"].value = 0

        # Allow ReadOnly phase and trigger the callback
        await ReadOnly()
        #PROMPT: The module clears the busy state, asserting `ex_if_ready_o`, allowing the execute stage to issue new requests.
        assert int(self.dut.ex_if_ready_o.value) ==1, f'dmem_req_o must be asserted'
        #PROMPT:
        # The data from DMEM is captured and forwarded to the writeback stage, sequentially.
        #       `wb_if_rvalid_o` is asserted  and  `wb_if_rdata_o` is written with dmem read data, **For one cycle**.
        if wb_check:
            assert int(self.dut.wb_if_rvalid_o.value) == 1 , f'WB SHOULD HAVE VALID DATA ON DMEM RDATA RSP'
            assert int(self.dut.wb_if_rdata_o.value) == rdata , f'WB DATA MISMATCH' 
            # NOTE: That value correctness depends on memory model(not RTL). Here We just verfying data is passed correctly to WB stage 

        # Hold the enable signal for one clock cycle
        await RisingEdge(self.clk)

        # Add a delay to simulate bus deactivation
        await NextTimeStep()

    
    
     
        
    