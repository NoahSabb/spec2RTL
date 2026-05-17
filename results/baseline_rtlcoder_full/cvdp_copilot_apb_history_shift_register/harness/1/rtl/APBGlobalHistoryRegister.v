If needed, use the following template for code block and comments:
Code Block Start: // start a new code block template enclosed in two consecutive empty lines. All the code between these lines is treated as a single indented code block. If additional indents are needed, place 4 or more consecutive space characters *before* any word, character, or punctuation. Code templates for predefined values: // integer: %d / signed integer: %d / float: %f / decimal: %b / octal: %o / hexadecimal: %x. Comment can be placed in template on next line (// is used to represent comment in verilog).
```vivado_template
module APBGlobalHistoryRegister( 
    input pclk,
    input presetn,           // Asynchronous reset for system initializations
    output reg pready,     // Ready signal driven high to indicate the end of a transaction.
    output reg [7:0] prdata,// Data bus for retrieving data from the module.
    input paddr, 
    input pselx,            // APB select signal, indicates CSR/memory selection.
    input penable,          // Enable signal marks transaction progression.
    input [7:0] pwdata,     // Write data bus for sending data to the module.
    output reg pslverr      // Error signal asserted on invalid addresses
);

// Register Descriptions:
reg[31:0] control_register;  
reg[7:0] train_history;
reg[7:0] predict_history; 

always @* begin
    pslverr = 1'b0;           // Default error signal.

    if (presetn == 0) begin
        control_register <= 32'd0;
        train_history <= 8'h0;
        predict_history <= 8'h0; 
        pready <= 1'b0;         // Reset the ready signal.
    end

    case ({paddr, pselx, penable})  // Detects which register is selected in APB. 
        3'd5: begin                     // Read-Only control_register
            prdata <= {8'b0, control_register[7:1]};   // Reserve address bit for error-flag.
            if (presetn == 0) begin       // In the reset state, ignore the read request with pready asserted.
                pready <= 1'b1;         // Set it high when a transaction is finished.
            end else begin
                case ({control_register[7:0]})
                    32'hxxxxxxxx: begin 
                        error_flag <= 1'b1;         
                        prdata <= {3'd8, 1'b0};   // Set the upper bits to an unreadable value.
                    end              
                    32'hxxxxxx8x: begin 
                        error_flag <= 1'b1;         
                        prdata <= {4'd8, 1'b0};   // Set the upper bits to an unreadable value.
                    end              
                    32'hdx: begin 
                        error_flag <= 1'b1;         
                        prdata <= {1'b1, 7'd0};      // Set the most significant bit high (unreadable).
                    end              
                    32'hxxxx: begin 
                        error_flag <= 1'b1;         
                        prdata <= 8'bx;             // Set the output port to a known state.
                    end              
                    default: begin 
                        error_flag <= 0;           // A valid address was selected, so clear the error-flag if one is set.
                        prdata <= control_register[7:0];   // Just pass back the requested value.
                    end      
                endcase               
                pready <= 1'b1;        
            end             
        end            
        3'd2: begin                     // Read-Only predict_history
            prdata <= predict_history[7:0];  
        end            
        3'd1: begin                     // Write-Only control_register
            if (presetn == 0) begin      // In the reset state, ignore write requests.
                pslverr <= 1'b1;         
            end else begin
                case ({control_register[7:0]})   // Check if a valid address is written.
                    32'hxxxxxxxx: begin 
                        error_flag <= 1'b1;          // Set the error-flag high.
                    end  
                    32'hdx: begin 
                        error_flag <= 1'b1;          // Set the error-flag high.
                    end   // Write-enable to memory-mapped register.  
 module mismatched_write <= 1'b1;         // Asserted only if a write to an unrecognized (unmapped) register is attempted.
                endcase             // Will match the cases above.
                
                predict_valid <= pwdata[0];   
                predict_taken <= pwdata[1];    
                train_history <= {train_history[6:0], pwdata[7]};   
                pslverr <= error_flag;           
            end             
        end        
    endcase      
end                         

// Clock Gating Enable
reg clk_gate_en;
always @(posedge pclk) begin
    if (~clk_gate_en) begin
        pready <= 1'b0;   // Drop the ready signal to prevent misaligned accesses.
    end
end

// Prediction Update Logic

always @(posedge history_shift_valid or negedge clk) begin
    if (~clk) begin
        // Handle the predict-branch update in case of a mispredicted branch. 
        if (train_mispredicted) begin
            predict_history <= {train_history, train_taken};
        end else if (predict_valid &&  ~train_mispredicted ) begin  
            // Handle the predict-branch update in case of a valid prediction.
            predict_history <= {predict_history[6:0], predict_taken};
        end
    end 
end

endmodule