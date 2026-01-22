#!/usr/bin/env python3
"""
Feature Extraction for Hardware Trojan Insertion
Implements SCOAP (Sandia Controllability/Observability Analysis)
and structural feature extraction
"""

import networkx as nx
import numpy as np
from pathlib import Path
import json
import argparse
from netlist_parser import parse_netlist, GateType


class FeatureExtractor:
    """Extract features for each net in the netlist"""
    
    def __init__(self, parser, graph):
        self.parser = parser
        self.graph = graph
        self.nets = parser.nets
        self.gates = parser.gates
        self.features = {}
    
    def extract_all_features(self):
        """Extract all features for all nets"""
        print("\nExtracting features...")
        
        # Structural features
        print("  Computing structural features...")
        self._compute_structural_features()
        
        # Testability features (SCOAP)
        print("  Computing SCOAP measures...")
        self._compute_scoap()
        
        # Graph-based features
        print("  Computing graph features...")
        self._compute_graph_features()
        
        # Compile features
        self._compile_features()
        
        print(f"  Extracted features for {len(self.features)} nets")
        
        return self.features
    
    def _compute_structural_features(self):
        """Compute basic structural features"""
        for net_name, net in self.nets.items():
            # Fan-in and fan-out
            net.fanin = self.graph.in_degree(net_name)
            net.fanout = self.graph.out_degree(net_name)
    
    def _compute_scoap(self):
        """
        Compute SCOAP (Sandia Controllability/Observability Analysis)
        
        Controllability: Difficulty of setting a net to 0 or 1
        Observability: Difficulty of observing a net's value at outputs
        
        Lower values = easier to control/observe
        Higher values = harder (better for hiding Trojans)
        """
        # Initialize
        for net_name in self.nets:
            self.nets[net_name].controllability_0 = float('inf')
            self.nets[net_name].controllability_1 = float('inf')
            self.nets[net_name].observability = float('inf')
        
        # Primary inputs have controllability = 1
        for pi in self.parser.primary_inputs:
            if pi in self.nets:
                self.nets[pi].controllability_0 = 1.0
                self.nets[pi].controllability_1 = 1.0
        
        # Forward pass: compute controllability
        self._compute_controllability()
        
        # Backward pass: compute observability
        self._compute_observability()
    
    def _compute_controllability(self):
        """Forward pass to compute controllability"""
        # Topological sort for forward traversal
        try:
            # Create subgraph without gate nodes for proper ordering
            net_graph = nx.DiGraph()
            for net_name in self.nets:
                net_graph.add_node(net_name)
            
            for gate_name, gate in self.gates.items():
                for inp in gate.inputs:
                    for out in gate.outputs:
                        if inp in self.nets and out in self.nets:
                            net_graph.add_edge(inp, out)
            
            topo_order = list(nx.topological_sort(net_graph))
        except:
            # If cyclic (has DFFs), use approximation
            topo_order = list(self.nets.keys())
        
        # Iterate multiple times for convergence
        for iteration in range(10):
            changed = False
            
            for gate_name, gate in self.gates.items():
                # Get input controllabilities
                input_c0 = []
                input_c1 = []
                
                for inp in gate.inputs:
                    if inp in self.nets:
                        input_c0.append(self.nets[inp].controllability_0)
                        input_c1.append(self.nets[inp].controllability_1)
                
                if not input_c0:
                    continue
                
                # Compute output controllability based on gate type
                out_c0, out_c1 = self._gate_controllability(
                    gate.gate_type, input_c0, input_c1
                )
                
                # Update output nets
                for out in gate.outputs:
                    if out in self.nets:
                        old_c0 = self.nets[out].controllability_0
                        old_c1 = self.nets[out].controllability_1
                        
                        self.nets[out].controllability_0 = min(
                            self.nets[out].controllability_0, out_c0
                        )
                        self.nets[out].controllability_1 = min(
                            self.nets[out].controllability_1, out_c1
                        )
                        
                        if (abs(self.nets[out].controllability_0 - old_c0) > 0.01 or
                            abs(self.nets[out].controllability_1 - old_c1) > 0.01):
                            changed = True
            
            if not changed:
                break
    
    def _gate_controllability(self, gate_type, input_c0, input_c1):
        """Compute output controllability based on gate type"""
        if gate_type == GateType.AND:
            # Output is 0 if any input is 0 (easy)
            # Output is 1 if all inputs are 1 (hard)
            c0 = min(input_c0) + 1
            c1 = sum(input_c1) + 1
            return c0, c1
        
        elif gate_type == GateType.NAND:
            c0 = sum(input_c1) + 1
            c1 = min(input_c0) + 1
            return c0, c1
        
        elif gate_type == GateType.OR:
            c0 = sum(input_c0) + 1
            c1 = min(input_c1) + 1
            return c0, c1
        
        elif gate_type == GateType.NOR:
            c0 = min(input_c1) + 1
            c1 = sum(input_c0) + 1
            return c0, c1
        
        elif gate_type == GateType.XOR or gate_type == GateType.XNOR:
            c0 = min(sum(input_c0), sum(input_c1)) + 1
            c1 = min(sum(input_c0), sum(input_c1)) + 1
            return c0, c1
        
        elif gate_type == GateType.NOT:
            c0 = input_c1[0] + 1 if input_c1 else 1
            c1 = input_c0[0] + 1 if input_c0 else 1
            return c0, c1
        
        elif gate_type == GateType.BUF:
            c0 = input_c0[0] + 1 if input_c0 else 1
            c1 = input_c1[0] + 1 if input_c1 else 1
            return c0, c1
        
        elif gate_type == GateType.DFF:
            # Flip-flop adds significant controllability
            c0 = input_c0[0] + 5 if input_c0 else 5
            c1 = input_c1[0] + 5 if input_c1 else 5
            return c0, c1
        
        elif gate_type == GateType.MUX:
            # Average of inputs
            c0 = sum(input_c0) / len(input_c0) + 2 if input_c0 else 2
            c1 = sum(input_c1) / len(input_c1) + 2 if input_c1 else 2
            return c0, c1
        
        else:  # Unknown gate type
            c0 = sum(input_c0) / len(input_c0) + 1 if input_c0 else 1
            c1 = sum(input_c1) / len(input_c1) + 1 if input_c1 else 1
            return c0, c1
    
    def _compute_observability(self):
        """Backward pass to compute observability"""
        # Primary outputs have observability = 0
        for po in self.parser.primary_outputs:
            if po in self.nets:
                self.nets[po].observability = 0.0
        
        # Backward traversal (from outputs to inputs)
        for iteration in range(10):
            changed = False
            
            for gate_name, gate in self.gates.items():
                # Get output observability
                output_obs = []
                for out in gate.outputs:
                    if out in self.nets:
                        output_obs.append(self.nets[out].observability)
                
                if not output_obs:
                    continue
                
                min_output_obs = min(output_obs)
                
                # Propagate to inputs
                for inp in gate.inputs:
                    if inp in self.nets:
                        # Input observability = output observability + controllability
                        # More complex gates make inputs harder to observe
                        new_obs = min_output_obs + len(gate.inputs)
                        
                        old_obs = self.nets[inp].observability
                        self.nets[inp].observability = min(
                            self.nets[inp].observability, new_obs
                        )
                        
                        if abs(self.nets[inp].observability - old_obs) > 0.01:
                            changed = True
            
            if not changed:
                break
    
    def _compute_graph_features(self):
        """Compute graph-based features"""
        # Logic depth (distance from primary inputs)
        for net_name, net in self.nets.items():
            if net.is_input:
                net.logic_depth = 0
            else:
                # Find shortest path from any primary input
                min_depth = float('inf')
                for pi in self.parser.primary_inputs:
                    if pi in self.graph and net_name in self.graph:
                        try:
                            path_len = nx.shortest_path_length(
                                self.graph, pi, net_name
                            )
                            min_depth = min(min_depth, path_len)
                        except nx.NetworkXNoPath:
                            pass
                
                net.logic_depth = min_depth if min_depth != float('inf') else 0
    
    def _compile_features(self):
        """Compile all features into feature dictionary"""
        for net_name, net in self.nets.items():
            # Skip primary inputs and outputs for Trojan insertion
            if net.is_input or net.is_output:
                continue
            
            # Normalize controllability and observability
            c0_norm = min(net.controllability_0, 100) / 100.0
            c1_norm = min(net.controllability_1, 100) / 100.0
            obs_norm = min(net.observability, 100) / 100.0
            
            self.features[net_name] = {
                'net_name': net_name,
                'fanin': net.fanin,
                'fanout': net.fanout,
                'logic_depth': net.logic_depth,
                'controllability_0': c0_norm,
                'controllability_1': c1_norm,
                'observability': obs_norm,
                'is_input': net.is_input,
                'is_output': net.is_output,
                
                # Derived features for Trojan insertion
                'avg_controllability': (c0_norm + c1_norm) / 2.0,
                'testability': (c0_norm + c1_norm) / 2.0 + obs_norm,  # Higher = harder to test
                'stealth_score': 0.0  # To be computed by ML model
            }


def extract_features_from_netlist(netlist_file, output_file=None):
    """Extract features from a netlist file"""
    # Parse netlist
    parser, graph = parse_netlist(netlist_file)
    
    # Extract features
    extractor = FeatureExtractor(parser, graph)
    features = extractor.extract_all_features()
    
    # Save to file
    if output_file:
        print(f"\nSaving features to {output_file}")
        
        # Convert to list format
        features_list = list(features.values())
        
        with open(output_file, 'w') as f:
            json.dump(features_list, f, indent=2)
        
        print(f"  Saved {len(features_list)} net features")
    
    return features


def main():
    parser = argparse.ArgumentParser(
        description='Extract features from gate-level netlist',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--netlist',
        required=True,
        help='Gate-level Verilog netlist'
    )
    
    parser.add_argument(
        '--output',
        required=True,
        help='Output JSON file with features'
    )
    
    args = parser.parse_args()
    
    features = extract_features_from_netlist(args.netlist, args.output)
    
    # Print statistics
    print("\nFeature statistics:")
    testability_scores = [f['testability'] for f in features.values()]
    print(f"  Testability: min={min(testability_scores):.3f}, "
          f"max={max(testability_scores):.3f}, "
          f"mean={np.mean(testability_scores):.3f}")


if __name__ == '__main__':
    main()
