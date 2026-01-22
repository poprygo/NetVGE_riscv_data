#!/usr/bin/env python3
"""
ML Detector Dataset Generation
Creates organized datasets for testing ML-based Hardware Trojan detectors
"""

import argparse
import json
import shutil
from pathlib import Path
from datetime import datetime
import random


def collect_netlists(directory, pattern='*.v'):
    """Collect all netlist files from directory"""
    dir_path = Path(directory)
    if not dir_path.exists():
        return []
    
    netlists = list(dir_path.rglob(pattern))
    return [str(n) for n in netlists]


def categorize_trojans(trojaned_netlists, metadata_file=None):
    """Categorize Trojans by difficulty/type"""
    
    categories = {
        'easy': [],
        'medium': [],
        'hard': [],
        'stealthy': []
    }
    
    if metadata_file and Path(metadata_file).exists():
        # Load metadata to categorize
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Categorize based on metadata
        for insertion in metadata.get('insertions', []):
            netlist = insertion.get('output_file')
            size = insertion.get('gates_added', 0)
            activation_prob = insertion.get('activation_probability', 1.0)
            
            # Categorization logic
            if size > 100 or activation_prob > 1e-3:
                categories['easy'].append(netlist)
            elif size < 20 and activation_prob < 1e-5:
                categories['stealthy'].append(netlist)
            elif activation_prob < 1e-4:
                categories['hard'].append(netlist)
            else:
                categories['medium'].append(netlist)
    else:
        # Simple categorization without metadata
        # Distribute evenly
        random.shuffle(trojaned_netlists)
        n = len(trojaned_netlists)
        categories['easy'] = trojaned_netlists[:n//4]
        categories['medium'] = trojaned_netlists[n//4:n//2]
        categories['hard'] = trojaned_netlists[n//2:3*n//4]
        categories['stealthy'] = trojaned_netlists[3*n//4:]
    
    return categories


def create_dataset_structure(output_dir, clean_netlists, trusthub_netlists, 
                            mimic_categories, train_ratio=0.7):
    """Create train/test split dataset structure"""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create directory structure
    train_dir = output_path / 'train'
    test_dir = output_path / 'test'
    
    for d in [train_dir, test_dir]:
        d.mkdir(exist_ok=True)
        (d / 'clean').mkdir(exist_ok=True)
        (d / 'trusthub_trojans').mkdir(exist_ok=True)
        for category in ['easy', 'medium', 'hard', 'stealthy']:
            (d / f'mimic_trojans_{category}').mkdir(exist_ok=True)
    
    dataset_info = {
        'created': datetime.now().isoformat(),
        'train_ratio': train_ratio,
        'splits': {
            'train': {},
            'test': {}
        }
    }
    
    # Split clean netlists
    random.shuffle(clean_netlists)
    n_train_clean = int(len(clean_netlists) * train_ratio)
    train_clean = clean_netlists[:n_train_clean]
    test_clean = clean_netlists[n_train_clean:]
    
    print(f"Clean netlists: {len(train_clean)} train, {len(test_clean)} test")
    
    # Copy clean netlists
    for netlists, split_dir, split_name in [(train_clean, train_dir, 'train'), 
                                              (test_clean, test_dir, 'test')]:
        for i, netlist in enumerate(netlists):
            dst = split_dir / 'clean' / f'clean_{i:03d}.v'
            shutil.copy(netlist, dst)
        dataset_info['splits'][split_name]['clean'] = len(netlists)
    
    # Split Trust-Hub netlists
    random.shuffle(trusthub_netlists)
    n_train_th = int(len(trusthub_netlists) * train_ratio)
    train_th = trusthub_netlists[:n_train_th]
    test_th = trusthub_netlists[n_train_th:]
    
    print(f"Trust-Hub trojans: {len(train_th)} train, {len(test_th)} test")
    
    for netlists, split_dir, split_name in [(train_th, train_dir, 'train'), 
                                              (test_th, test_dir, 'test')]:
        for i, netlist in enumerate(netlists):
            dst = split_dir / 'trusthub_trojans' / f'trusthub_{i:03d}.v'
            shutil.copy(netlist, dst)
        dataset_info['splits'][split_name]['trusthub_trojans'] = len(netlists)
    
    # Split MIMIC Trojans by category
    for category, netlists in mimic_categories.items():
        if not netlists:
            continue
        
        random.shuffle(netlists)
        
        # For easy category, use more for training
        # For hard/stealthy, use more for testing
        if category == 'easy':
            split_ratio = 0.8
        elif category in ['hard', 'stealthy']:
            split_ratio = 0.3
        else:
            split_ratio = train_ratio
        
        n_train = int(len(netlists) * split_ratio)
        train_netlists = netlists[:n_train]
        test_netlists = netlists[n_train:]
        
        print(f"MIMIC {category}: {len(train_netlists)} train, {len(test_netlists)} test")
        
        # Copy to train
        for i, netlist in enumerate(train_netlists):
            dst = train_dir / f'mimic_trojans_{category}' / f'mimic_{category}_{i:03d}.v'
            shutil.copy(netlist, dst)
        
        # Copy to test
        for i, netlist in enumerate(test_netlists):
            dst = test_dir / f'mimic_trojans_{category}' / f'mimic_{category}_{i:03d}.v'
            shutil.copy(netlist, dst)
        
        dataset_info['splits']['train'][f'mimic_{category}'] = len(train_netlists)
        dataset_info['splits']['test'][f'mimic_{category}'] = len(test_netlists)
    
    return dataset_info


def create_labels_csv(output_dir, dataset_info):
    """Create CSV with labels for all samples"""
    
    import csv
    
    labels_file = Path(output_dir) / 'labels.csv'
    
    with open(labels_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['file', 'split', 'label', 'category', 'trojan_type'])
        
        for split in ['train', 'test']:
            split_dir = Path(output_dir) / split
            
            # Clean samples
            for netlist in (split_dir / 'clean').glob('*.v'):
                writer.writerow([
                    str(netlist.relative_to(output_dir)),
                    split,
                    0,  # Clean
                    'clean',
                    'none'
                ])
            
            # Trust-Hub samples
            for netlist in (split_dir / 'trusthub_trojans').glob('*.v'):
                writer.writerow([
                    str(netlist.relative_to(output_dir)),
                    split,
                    1,  # Trojaned
                    'trusthub',
                    'trusthub'
                ])
            
            # MIMIC samples
            for category in ['easy', 'medium', 'hard', 'stealthy']:
                category_dir = split_dir / f'mimic_trojans_{category}'
                if category_dir.exists():
                    for netlist in category_dir.glob('*.v'):
                        writer.writerow([
                            str(netlist.relative_to(output_dir)),
                            split,
                            1,  # Trojaned
                            'mimic',
                            category
                        ])
    
    print(f"Labels saved: {labels_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate ML detector dataset from netlists',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--clean',
        required=True,
        help='Directory with clean netlists'
    )
    
    parser.add_argument(
        '--mimic',
        required=True,
        help='Directory with MIMIC-inserted netlists'
    )
    
    parser.add_argument(
        '--trusthub',
        help='Directory with Trust-Hub Trojan netlists (optional)'
    )
    
    parser.add_argument(
        '--metadata',
        help='MIMIC metadata JSON file for categorization'
    )
    
    parser.add_argument(
        '--output',
        required=True,
        help='Output dataset directory'
    )
    
    parser.add_argument(
        '--train-ratio',
        type=float,
        default=0.7,
        help='Ratio of data for training'
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility'
    )
    
    args = parser.parse_args()
    
    # Set random seed
    random.seed(args.seed)
    
    print("="*60)
    print("ML Detector Dataset Generation")
    print("="*60)
    
    # Collect netlists
    print("\nCollecting netlists...")
    clean_netlists = collect_netlists(args.clean)
    print(f"  Clean: {len(clean_netlists)}")
    
    mimic_netlists = collect_netlists(args.mimic)
    print(f"  MIMIC: {len(mimic_netlists)}")
    
    trusthub_netlists = []
    if args.trusthub:
        trusthub_netlists = collect_netlists(args.trusthub)
        print(f"  Trust-Hub: {len(trusthub_netlists)}")
    
    if not clean_netlists:
        print("Error: No clean netlists found")
        return 1
    
    if not mimic_netlists:
        print("Error: No MIMIC netlists found")
        return 1
    
    # Categorize MIMIC Trojans
    print("\nCategorizing MIMIC Trojans...")
    mimic_categories = categorize_trojans(mimic_netlists, args.metadata)
    for category, netlists in mimic_categories.items():
        print(f"  {category}: {len(netlists)}")
    
    # Create dataset structure
    print(f"\nCreating dataset structure...")
    dataset_info = create_dataset_structure(
        args.output,
        clean_netlists,
        trusthub_netlists,
        mimic_categories,
        args.train_ratio
    )
    
    # Save dataset info
    info_file = Path(args.output) / 'dataset_info.json'
    with open(info_file, 'w') as f:
        json.dump(dataset_info, f, indent=2)
    print(f"\nDataset info saved: {info_file}")
    
    # Create labels CSV
    print("\nGenerating labels CSV...")
    create_labels_csv(args.output, dataset_info)
    
    # Summary
    print("\n" + "="*60)
    print("Dataset Generation Complete!")
    print("="*60)
    print(f"Output directory: {args.output}")
    print("\nDataset composition:")
    print("  Train:")
    for key, value in dataset_info['splits']['train'].items():
        print(f"    {key}: {value}")
    print("  Test:")
    for key, value in dataset_info['splits']['test'].items():
        print(f"    {key}: {value}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
