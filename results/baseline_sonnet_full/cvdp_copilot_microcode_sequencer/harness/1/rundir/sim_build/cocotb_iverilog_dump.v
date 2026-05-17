module cocotb_iverilog_dump();
initial begin
    string dumpfile_path;    if ($value$plusargs("dumpfile_path=%s", dumpfile_path)) begin
        $dumpfile(dumpfile_path);
    end else begin
        $dumpfile("/code/rundir/sim_build/microcode_sequencer.fst");
    end
    $dumpvars(0, microcode_sequencer);
end
endmodule
