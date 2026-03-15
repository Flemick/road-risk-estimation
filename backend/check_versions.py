import importlib.metadata
import sys

packages = ['scikit-learn', 'joblib', 'Flask', 'requests', 'python-dotenv', 'Flask-SQLAlchemy', 'Flask-Login', 'Werkzeug', 'pandas', 'numpy']

with open('c:/Users/LENOVO/Desktop/projects/accident_risk/backend/system_versions.txt', 'w') as f:
    for pkg in packages:
        try:
            v = importlib.metadata.version(pkg)
            f.write(f"{pkg}=={v}\n")
        except Exception as e:
            f.write(f"{pkg} == NOT INSTALLED\n")
