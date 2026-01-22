#!/usr/bin/env python3
"""
Netlist Parser and Graph Builder
Parses gate-level Verilog netlists and builds graph representation
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
import networkx as nx


class GateType:
    """Gate types in the netlist"""
    AND = 'AND'
    OR = 'OR'
    XOR = 'XOR'
    NAND = 'NAND'
    NOR = 'NOR'
    XNOR = 'XNOR'
    NOT = 'NOT'
    BUF = 'BUF'
    DFF = 'DFF'
    MUX = 'MUX'
    UNKNOWN = 'UNKNOWN'


class NetlistParser:
    """Parse gate-level Verilog netlist"""
    
    def __init__(self, netlist_file):
        self.netlist_file = netlist_file
        self.graph = nx.DiGraph()
        self.nets = {}  # net_name -> Net object
        self.gates = {}  # gate_name -> Gate object
        self.primary_inputs = set()
        self.primary_outputs = set()
        self.module_name = None
        
    def parse(self):
        """Parse the netlist file"""
        print(f"Parsing netlist: {self.netlist_file}")
        
        with open(self.netlist_file, 'r') as f:
            content = f.read()
        
        # Remove comments
        content = self._remove_comments(content)
        
        # Extract module info
        self._parse_module_header(content)
        
        # Parse ports
        self._parse_ports(content)
        
        # Parse wires
        self._parse_wires(content)
        
        # Parse gate instances
        self._parse_gates(content)
        
        # Build graph
        self._build_graph()
        
        print(f"  Parsed: {len(self.gates)} gates, {len(self.nets)} nets")
        print(f"  Primary inputs: {len(self.primary_inputs)}")
        print(f"  Primary outputs: {len(self.primary_outputs)}")
        
        return self.graph
    
    def _remove_comments(self, content):
        """Remove single-line and multi-line comments"""
        # Remove single-line comments
        content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        return content
    
    def _parse_module_header(self, content):
        """Extract module name"""
        match = re.search(r'module\s+(\w+)\s*\(', content)
        if match:
            self.module_name = match.group(1)
            print(f"  Module: {self.module_name}")
    
    def _parse_ports(self, content):
        """Parse input/output ports"""
        # Input ports
        for match in re.finditer(r'input\s+(?:\[.*?\]\s+)?(\w+)', content):
            port_name = match.group(1)
            self.primary_inputs.add(port_name)
            self.nets[port_name] = Net(port_name, is_input=True)
        
        # Output ports
        for match in re.finditer(r'output\s+(?:\[.*?\]\s+)?(\w+)', content):
            port_name = match.group(1)
            self.primary_outputs.add(port_name)
            if port_name not in self.nets:
                self.nets[port_name] = Net(port_name, is_output=True)
            else:
                self.nets[port_name].is_output = True
    
    def _parse_wires(self, content):
        """Parse wire declarations"""
        for match in re.finditer(r'wire\s+(?:\[.*?\]\s+)?(\w+)', content):
            wire_name = match.group(1)
            if wire_name not in self.nets:
                self.nets[wire_name] = Net(wire_name)
    
    def _parse_gates(self, content):
        """Parse gate instances"""
        # Pattern for gate instantiation: GATETYPE INSTANCENAME (.A(net1), .Y(net2));
        pattern = r'(\w+)\s+(\w+)\s*\((.*?)\);'
        
        for match in re.finditer(pattern, content, re.DOTALL):
            gate_type_str = match.group(1)
            instance_name = match.group(2)
            connections = match.group(3)
            
            # Skip module/endmodule
            if gate_type_str in ['module', 'endmodule', 'input', 'output', 'wire']:
                continue
            
            # Parse connections
            inputs = []
            outputs = []
            
            for conn in re.finditer(r'\.(\w+)\s*\((\w+)\)', connections):
                port = conn.group(1)
                net = conn.group(2)
                
                # Determine if input or output based on port name
                if port in ['Y', 'Q', 'QN', 'Z', 'ZN', 'OUT']:
                    outputs.append(net)
                else:
                    inputs.append(net)
                
                # Ensure net exists
                if net not in self.nets:
                    self.nets[net] = Net(net)
            
            # Create gate
            gate_type = self._classify_gate_type(gate_type_str)
            gate = Gate(instance_name, gate_type, gate_type_str, inputs, outputs)
            self.gates[instance_name] = gate
    
    def _classify_gate_type(self, gate_type_str):
        """Classify gate type from cell name"""
        gate_str = gate_type_str.upper()
        
        if 'AND' in gate_str and 'NAND' not in gate_str:
            return GateType.AND
        elif 'NAND' in gate_str:
            return GateType.NAND
        elif 'OR' in gate_str and 'NOR' not in gate_str and 'XOR' not in gate_str:
            return GateType.OR
        elif 'NOR' in gate_str and 'XNOR' not in gate_str:
            return GateType.NOR
        elif 'XOR' in gate_str and 'XNOR' not in gate_str:
            return GateType.XOR
        elif 'XNOR' in gate_str:
            return GateType.XNOR
        elif 'NOT' in gate_str or 'INV' in gate_str:
            return GateType.NOT
        elif 'BUF' in gate_str:
            return GateType.BUF
        elif 'DFF' in gate_str or 'DFFR' in gate_str or 'DFFS' in gate_str:
            return GateType.DFF
        elif 'MUX' in gate_str:
            return GateType.MUX
        else:
            return GateType.UNKNOWN
    
    def _build_graph(self):
        """Build NetworkX graph from parsed data"""
        # Add nodes for each net
        for net_name, net in self.nets.items():
            self.graph.add_node(net_name, 
                              type='net',
                              is_input=net.is_input,
                              is_output=net.is_output,
                              net_obj=net)
        
        # Add edges based on gate connections
        for gate_name, gate in self.gates.items():
            # Add gate as node
            self.graph.add_node(gate_name,
                              type='gate',
                              gate_type=gate.gate_type,
                              gate_obj=gate)
            
            # Connect inputs to gate
            for input_net in gate.inputs:
                if input_net in self.nets:
                    self.graph.add_edge(input_net, gate_name)
            
            # Connect gate to outputs
            for output_net in gate.outputs:
                if output_net in self.nets:
                    self.graph.add_edge(gate_name, output_net)


class Net:
    """Represents a net (wire) in the netlist"""
    
    def __init__(self, name, is_input=False, is_output=False):
        self.name = name
        self.is_input = is_input
        self.is_output = is_output
        self.driver = None  # Gate that drives this net
        self.loads = []  # Gates that read this net
        
        # Features (to be computed)
        self.fanin = 0
        self.fanout = 0
        self.logic_depth = 0
        self.controllability_0 = 0.0
        self.controllability_1 = 0.0
        self.observability = 0.0
        self.switching_probability = 0.0
    
    def __repr__(self):
        return f"Net({self.name}, fanin={self.fanin}, fanout={self.fanout})"


class Gate:
    """Represents a gate in the netlist"""
    
    def __init__(self, name, gate_type, cell_name, inputs, outputs):
        self.name = name
        self.gate_type = gate_type
        self.cell_name = cell_name
        self.inputs = inputs
        self.outputs = outputs
    
    def __repr__(self):
        return f"Gate({self.name}, {self.gate_type}, in={len(self.inputs)}, out={len(self.outputs)})"


def parse_netlist(netlist_file):
    """Convenience function to parse netlist"""
    parser = NetlistParser(netlist_file)
    graph = parser.parse()
    return parser, graph


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python netlist_parser.py <netlist.v>")
        sys.exit(1)
    
    parser, graph = parse_netlist(sys.argv[1])
    
    print("\nGraph statistics:")
    print(f"  Nodes: {graph.number_of_nodes()}")
    print(f"  Edges: {graph.number_of_edges()}")
    print(f"  Connected: {nx.is_weakly_connected(graph)}")
