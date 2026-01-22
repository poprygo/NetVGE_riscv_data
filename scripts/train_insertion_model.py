#!/usr/bin/env python3
"""
Train Trojan Insertion Model
Learn from Trust-Hub Trojans to identify vulnerable nets
Uses LightGBM or Random Forest as in MIMIC paper
"""

import argparse
import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, roc_auc_score
import joblib


class TrojanInsertionModel:
    """Train model to identify nets suitable for Trojan insertion"""
    
    def __init__(self, model_type='random_forest'):
        self.model_type = model_type
        self.model = None
        self.feature_columns = None
        
    def prepare_training_data(self, trusthub_features_dir):
        """
        Prepare training data from Trust-Hub Trojans
        
        Args:
            trusthub_features_dir: Directory with extracted features from
                                   both clean and Trojaned Trust-Hub designs
        """
        print("Preparing training data...")
        
        X_list = []
        y_list = []
        
        # Load features from Trust-Hub designs
        features_dir = Path(trusthub_features_dir)
        
        for features_file in features_dir.glob('*.json'):
            print(f"  Loading {features_file.name}")
            
            with open(features_file, 'r') as f:
                features = json.load(f)
            
            # Determine if this is a Trojaned design
            is_trojaned = 'trojan' in features_file.name.lower()
            
            # Convert to DataFrame
            df = pd.DataFrame(features)
            
            # For Trojaned designs, label nets near Trojan as positive
            # For clean designs, all nets are negative
            if is_trojaned:
                # Heuristic: Mark nets with high testability as Trojan locations
                # In real implementation, you'd parse the Trojan metadata
                threshold = df['testability'].quantile(0.9)
                labels = (df['testability'] >= threshold).astype(int)
            else:
                labels = np.zeros(len(df))
            
            X_list.append(df)
            y_list.extend(labels)
        
        if not X_list:
            raise ValueError("No feature files found in directory")
        
        # Combine all data
        X = pd.concat(X_list, ignore_index=True)
        y = np.array(y_list)
        
        # Select feature columns
        self.feature_columns = [
            'fanin', 'fanout', 'logic_depth',
            'controllability_0', 'controllability_1',
            'observability', 'avg_controllability', 'testability'
        ]
        
        X = X[self.feature_columns]
        
        print(f"\nTraining data:")
        print(f"  Samples: {len(X)}")
        print(f"  Features: {len(self.feature_columns)}")
        print(f"  Positive (Trojan sites): {y.sum()}")
        print(f"  Negative (Clean sites): {(1-y).sum()}")
        
        return X, y
    
    def train(self, X, y):
        """Train the insertion model"""
        print(f"\nTraining {self.model_type} model...")
        
        if self.model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=10,
                min_samples_leaf=5,
                class_weight='balanced',  # Handle imbalanced data
                random_state=42,
                n_jobs=-1
            )
        
        elif self.model_type == 'gradient_boosting':
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                min_samples_split=10,
                min_samples_leaf=5,
                random_state=42
            )
        
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
        
        # Train model
        self.model.fit(X, y)
        
        print("  Training complete!")
        
        # Feature importance
        self._print_feature_importance(X.columns)
        
        return self.model
    
    def evaluate(self, X, y):
        """Evaluate model performance"""
        print("\nEvaluating model...")
        
        # Split for evaluation
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, random_state=42, stratify=y
        )
        
        # Train on subset
        self.model.fit(X_train, y_train)
        
        # Predict
        y_pred = self.model.predict(X_test)
        y_prob = self.model.predict_proba(X_test)[:, 1]
        
        # Metrics
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))
        
        try:
            roc_auc = roc_auc_score(y_test, y_prob)
            print(f"\nROC-AUC Score: {roc_auc:.4f}")
        except:
            print("ROC-AUC not computed (may need more positive samples)")
        
        # Cross-validation
        cv_scores = cross_val_score(self.model, X, y, cv=5, scoring='accuracy')
        print(f"\nCross-validation accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
    
    def _print_feature_importance(self, feature_names):
        """Print feature importance"""
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            indices = np.argsort(importances)[::-1]
            
            print("\nFeature Importance:")
            for i, idx in enumerate(indices[:10]):  # Top 10
                print(f"  {i+1}. {feature_names[idx]}: {importances[idx]:.4f}")
    
    def predict_trojan_sites(self, features_file, top_k=100):
        """
        Predict top-k nets suitable for Trojan insertion
        
        Args:
            features_file: JSON file with net features
            top_k: Number of top nets to return
        
        Returns:
            List of (net_name, score) tuples
        """
        print(f"\nPredicting Trojan insertion sites...")
        
        # Load features
        with open(features_file, 'r') as f:
            features = json.load(f)
        
        df = pd.DataFrame(features)
        
        # Extract feature columns
        X = df[self.feature_columns]
        
        # Predict probabilities
        scores = self.model.predict_proba(X)[:, 1]
        
        # Add to dataframe
        df['stealth_score'] = scores
        
        # Sort by score (descending)
        df_sorted = df.sort_values('stealth_score', ascending=False)
        
        # Get top-k
        top_nets = df_sorted.head(top_k)
        
        print(f"  Top {top_k} nets selected")
        print(f"  Score range: {top_nets['stealth_score'].min():.4f} - {top_nets['stealth_score'].max():.4f}")
        
        return list(zip(top_nets['net_name'], top_nets['stealth_score']))
    
    def save(self, output_file):
        """Save trained model"""
        if self.model is None:
            raise ValueError("Model not trained yet")
        
        model_data = {
            'model': self.model,
            'model_type': self.model_type,
            'feature_columns': self.feature_columns
        }
        
        joblib.dump(model_data, output_file)
        print(f"\nModel saved to {output_file}")
    
    @classmethod
    def load(cls, model_file):
        """Load trained model"""
        model_data = joblib.load(model_file)
        
        instance = cls(model_type=model_data['model_type'])
        instance.model = model_data['model']
        instance.feature_columns = model_data['feature_columns']
        
        print(f"Model loaded from {model_file}")
        return instance


def generate_synthetic_training_data():
    """
    Generate synthetic training data when Trust-Hub features are not available
    Based on Trojan insertion principles from literature
    """
    print("\nGenerating synthetic training data...")
    print("(Use this only if Trust-Hub features are unavailable)")
    
    n_samples = 10000
    
    # Generate random features
    np.random.seed(42)
    
    fanin = np.random.randint(1, 10, n_samples)
    fanout = np.random.randint(1, 20, n_samples)
    logic_depth = np.random.randint(1, 50, n_samples)
    controllability_0 = np.random.uniform(0, 1, n_samples)
    controllability_1 = np.random.uniform(0, 1, n_samples)
    observability = np.random.uniform(0, 1, n_samples)
    
    # Compute derived features
    avg_controllability = (controllability_0 + controllability_1) / 2.0
    testability = avg_controllability + observability
    
    # Create DataFrame
    X = pd.DataFrame({
        'fanin': fanin,
        'fanout': fanout,
        'logic_depth': logic_depth,
        'controllability_0': controllability_0,
        'controllability_1': controllability_1,
        'observability': observability,
        'avg_controllability': avg_controllability,
        'testability': testability
    })
    
    # Generate labels based on Trojan insertion principles:
    # Good Trojan sites have:
    # - High controllability (hard to control) → high values
    # - High observability (hard to observe) → high values
    # - Medium logic depth (not too shallow, not too deep)
    # - Moderate fanout (enough to impact functionality)
    
    score = (
        0.3 * avg_controllability +
        0.3 * observability +
        0.2 * (1.0 - np.abs(logic_depth - 25) / 25.0) +  # Prefer depth ~25
        0.2 * (fanout / 20.0)
    )
    
    # Label top 10% as Trojan sites
    threshold = np.percentile(score, 90)
    y = (score >= threshold).astype(int)
    
    print(f"  Generated {n_samples} samples")
    print(f"  Positive samples: {y.sum()}")
    
    return X, y


def main():
    parser = argparse.ArgumentParser(
        description='Train Trojan insertion model',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--features-dir',
        help='Directory with Trust-Hub feature JSON files'
    )
    
    parser.add_argument(
        '--synthetic',
        action='store_true',
        help='Use synthetic training data (if Trust-Hub not available)'
    )
    
    parser.add_argument(
        '--model-type',
        choices=['random_forest', 'gradient_boosting'],
        default='random_forest',
        help='Type of model to train'
    )
    
    parser.add_argument(
        '--output',
        required=True,
        help='Output model file (.pkl)'
    )
    
    parser.add_argument(
        '--evaluate',
        action='store_true',
        help='Perform model evaluation'
    )
    
    args = parser.parse_args()
    
    # Create model
    model = TrojanInsertionModel(model_type=args.model_type)
    
    # Prepare training data
    if args.synthetic:
        X, y = generate_synthetic_training_data()
        model.feature_columns = X.columns.tolist()
    elif args.features_dir:
        X, y = model.prepare_training_data(args.features_dir)
    else:
        print("Error: Must specify either --features-dir or --synthetic")
        return 1
    
    # Train
    model.train(X, y)
    
    # Evaluate
    if args.evaluate:
        model.evaluate(X, y)
    
    # Save
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    model.save(args.output)
    
    print("\n✓ Training complete!")
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
