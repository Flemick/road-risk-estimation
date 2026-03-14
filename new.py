import joblib
model = joblib.load("forest_model.pkl")
print(type(model))
feature_columns = joblib.load("feature_columns.pkl")
print(type(feature_columns))
print(model.classes_)
