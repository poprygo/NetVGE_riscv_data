#!/usr/bin/env python3
"""
End-to-End MIMIC Pipeline
Complete workflow for automatic Hardware Trojan insertion
Based on Cruz et al. "Automatic Hardware Trojan Insertion using Machine Learning"
"""

import argparse
import json
from pathlib import Path
import sys

# Import our custom modules
from feature_extraction import extract_features_from_netlist
from train_insertion_model import TrojanInsertionModel
from trojan_inserter import insert_multiple_trojans


def run_mimic_pipeline(
    netlist_file,
    output_dir,
    num_trojans=10,
    model_file=None,
    use_synthetic_training=True
):
    """
    Run complete MIMIC pipeline
    
    Steps:
    1. Extract features from netlist (SCOAP + structural)
    2. Train/load model to identify vulnerable nets
    3. Score nets and select top candidates
    4. Insert Trojans into netlist
    
    Args:
        netlist_file: Input gate-level netlist
        output_dir: Output directory for results
        num_trojans: Number of Trojans to insert
        model_file: Pre-trained model file (if available)
        use_synthetic_training: Use synthetic training data
    
    Returns:
        Dict with pipeline results
    """
    
    print("="*70)
    print("MIMIC: Automatic Hardware Trojan Insertion Pipeline")
    print("="*70)
    print(f"\nInput netlist: {netlist_file}")
    print(f"Output directory: {output_dir}")
    print(f"Number of Trojans: {num_trojans}")
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # ========================================================================
    # STEP 1: Feature Extraction
    # ========================================================================
    print("\n" + "="*70)
    print("STEP 1: Feature Extraction (SCOAP + Structural)")
    print("="*70)
    
    features_file = output_path / 'netlist_features.json'
    
    print("\nExtracting features from netlist...")
    print("This includes:")
    print("  - Structural features (fan-in, fan-out, logic depth)")
    print("  - SCOAP measures (controllability, observability)")
    print("  - Testability scores")
    
    features = extract_features_from_netlist(netlist_file, features_file)
    
    if not features:
        print("Error: Feature extraction failed")
        return None
    
    print(f"\n✓ Feature extraction complete")
    print(f"  Extracted features for {len(features)} nets")
    print(f"  Features saved to: {features_file}")
    
    # ========================================================================
    # STEP 2: Train/Load Insertion Model
    # ========================================================================
    print("\n" + "="*70)
    print("STEP 2: Train Trojan Insertion Model")
    print("="*70)
    
    model_path = output_path / 'insertion_model.pkl'
    
    if model_file and Path(model_file).exists():
        print(f"\nLoading pre-trained model from {model_file}")
        model = TrojanInsertionModel.load(model_file)
    else:
        print("\nTraining new model...")
        
        if use_synthetic_training:
            print("Using synthetic training data (Trust-Hub not available)")
            print("\nModel learns to identify nets that are:")
            print("  - Hard to control (high controllability)")
            print("  - Hard to observe (high observability)")
            print("  - At medium logic depth")
            print("  - With moderate fan-out")
            
            model = TrojanInsertionModel(model_type='random_forest')
            
            # Generate synthetic training data
            from train_insertion_model import generate_synthetic_training_data
            X, y = generate_synthetic_training_data()
            
            # Set feature columns manually
            model.feature_columns = X.columns.tolist()
            
            # Train
            model.train(X, y)
        else:
            # Would use Trust-Hub here if available
            print("Error: Trust-Hub training data not implemented yet")
            print("Use --synthetic flag to train on synthetic data")
            return None
        
        # Save model
        model.save(model_path)
    
    print(f"\n✓ Model ready")
    
    # ========================================================================
    # STEP 3: Score Nets and Select Candidates
    # ========================================================================
    print("\n" + "="*70)
    print("STEP 3: Score Nets and Select Trojan Insertion Sites")
    print("="*70)
    
    print("\nScoring all nets in the design...")
    print("Model predicts probability that each net is suitable for Trojan insertion")
    
    top_k = num_trojans * 10  # Get more candidates than needed
    target_nets = model.predict_trojan_sites(features_file, top_k=top_k)
    
    # Save target nets
    target_nets_file = output_path / 'target_nets.json'
    with open(target_nets_file, 'w') as f:
        json.dump({
            'num_nets': len(target_nets),
            'target_nets': target_nets
        }, f, indent=2)
    
    print(f"\n✓ Selected {len(target_nets)} candidate nets")
    print(f"  Target nets saved to: {target_nets_file}")
    
    # Print top 10
    print("\nTop 10 nets for Trojan insertion:")
    for i, (net_name, score) in enumerate(target_nets[:10], 1):
        print(f"  {i:2d}. {net_name:30s} (score: {score:.4f})")
    
    # ========================================================================
    # STEP 4: Insert Trojans
    # ========================================================================
    print("\n" + "="*70)
    print("STEP 4: Automatic Trojan Insertion")
    print("="*70)
    
    print(f"\nInserting {num_trojans} Trojans...")
    print("For each Trojan:")
    print("  - Randomly select trigger type (combinational/sequential/counter)")
    print("  - Randomly select payload type (leakage/dos/corruption)")
    print("  - Connect trigger to high-scoring nets")
    print("  - Connect payload to critical signals")
    
    trojans_dir = output_path / 'trojaned_netlists'
    
    results = insert_multiple_trojans(
        netlist_file,
        target_nets,
        num_trojans,
        trojans_dir
    )
    
    print(f"\n✓ Trojan insertion complete")
    print(f"  Generated {len(results)} Trojaned netlists")
    print(f"  Output directory: {trojans_dir}")
    
    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "="*70)
    print("PIPELINE COMPLETE")
    print("="*70)
    
    # Compile summary
    summary = {
        'input_netlist': str(netlist_file),
        'output_directory': str(output_dir),
        'num_trojans_requested': num_trojans,
        'num_trojans_inserted': len(results),
        'features_file': str(features_file),
        'model_file': str(model_path),
        'target_nets_file': str(target_nets_file),
        'trojaned_netlists_dir': str(trojans_dir),
        'metadata_file': str(trojans_dir / 'insertion_metadata.json')
    }
    
    # Save summary
    summary_file = output_path / 'pipeline_summary.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("\nSummary:")
    print(f"  Input: {netlist_file}")
    print(f"  Output: {output_dir}")
    print(f"  Trojans inserted: {len(results)}")
    print(f"  Summary saved to: {summary_file}")
    
    print("\nNext steps:")
    print("  1. Validate insertions: python scripts/validate_insertion.py ...")
    print("  2. Generate ML dataset: python scripts/generate_dataset.py ...")
    print("  3. Test your ML detector on the new dataset")
    
    print("\n" + "="*70)
    
    return summary


def main():
    parser = argparse.ArgumentParser(
        description='Run complete MIMIC pipeline for Hardware Trojan insertion',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="""
Example usage:
  # Basic usage with synthetic training
  python mimic_pipeline.py \\
      --netlist synthesis/netlists/picorv32_gl.v \\
      --output trojans/mimic_output/ \\
      --num-trojans 50

  # Use pre-trained model
  python mimic_pipeline.py \\
      --netlist synthesis/netlists/picorv32_gl.v \\
      --output trojans/mimic_output/ \\
      --model trojans/models/insertion_model.pkl \\
      --num-trojans 100
        """
    )
    
    parser.add_argument(
        '--netlist',
        required=True,
        help='Input gate-level Verilog netlist'
    )
    
    parser.add_argument(
        '--output',
        required=True,
        help='Output directory for all results'
    )
    
    parser.add_argument(
        '--num-trojans',
        type=int,
        default=10,
        help='Number of Trojans to insert'
    )
    
    parser.add_argument(
        '--model',
        help='Pre-trained model file (.pkl). If not provided, trains new model'
    )
    
    parser.add_argument(
        '--synthetic',
        action='store_true',
        default=True,
        help='Use synthetic training data (default: True)'
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility'
    )
    
    args = parser.parse_args()
    
    # Set random seed
    import random
    import numpy as np
    random.seed(args.seed)
    np.random.seed(args.seed)
    
    # Check input exists
    if not Path(args.netlist).exists():
        print(f"Error: Netlist file not found: {args.netlist}")
        return 1
    
    # Run pipeline
    try:
        summary = run_mimic_pipeline(
            netlist_file=args.netlist,
            output_dir=args.output,
            num_trojans=args.num_trojans,
            model_file=args.model,
            use_synthetic_training=args.synthetic
        )
        
        if summary:
            return 0
        else:
            return 1
    
    except Exception as e:
        print(f"\nError running pipeline: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
