"""
Kaggle Toolkit for interacting with Kaggle competitions and datasets.
Mocks the behavior of the official Kaggle API for the Green Agent environment.
"""
from pathlib import Path
import json
import os
import shutil

class KaggleToolkit:
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self.data_dir = workspace_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def download_competition_data(self, competition_name: str):
        """Mock download of competition data."""
        target_dir = self.data_dir / competition_name
        target_dir.mkdir(exist_ok=True)
        
        # Create mock data files
        if competition_name == "titanic":
            self._create_titanic_data(target_dir)
        elif competition_name == "cifar10":
            self._create_cifar_data(target_dir)
        
        return str(target_dir)

    def _create_titanic_data(self, target_dir: Path):
        """Create mock Titanic CSVs."""
        train_csv = target_dir / "train.csv"
        test_csv = target_dir / "test.csv"
        
        # Minimal mock data
        with open(train_csv, "w") as f:
            f.write("PassengerId,Survived,Pclass,Name,Sex,Age,SibSp,Parch,Ticket,Fare,Cabin,Embarked\n")
            f.write("1,0,3,\"Braund, Mr. Owen Harris\",male,22,1,0,A/5 21171,7.25,,S\n")
            f.write("2,1,1,\"Cumings, Mrs. John Bradley (Florence Briggs Thayer)\",female,38,1,0,PC 17599,71.2833,C85,C\n")

        with open(test_csv, "w") as f:
            f.write("PassengerId,Pclass,Name,Sex,Age,SibSp,Parch,Ticket,Fare,Cabin,Embarked\n")
            f.write("892,3,\"Kelly, Mr. James\",male,34.5,0,0,330911,7.8292,,Q\n")

    def _create_cifar_data(self, target_dir: Path):
        """Create mock CIFAR placeholders."""
        (target_dir / "data_batch_1.bin").touch()
        (target_dir / "test_batch.bin").touch()
