import os
import json
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import confusion_matrix, classification_report
import seaborn as sns
import matplotlib.pyplot as plt
import joblib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def evaluate_sensor_model():
    print("\n" + "="*50)
    print("1. SENSOR MODEL EVALUATION (GradientBoosting)")
    print("="*50)
    
    # Load test data and model
    csv_path = os.path.join(BASE_DIR, "plant_disease_dataset_new.csv")
    if not os.path.exists(csv_path):
        print("Sensor dataset not found. Run train_sensor_model.py first.")
        return
        
    df = pd.read_csv(csv_path)
    X = df[["Temp", "Humidity", "Soil"]]
    y_true = df["Disease"]
    
    model_path = os.path.join(BASE_DIR, "sensor_disease_model.joblib")
    model = joblib.load(model_path)
    
    y_pred = model.predict(X)
    
    # Accuracy and report
    print(classification_report(y_true, y_pred))
    
    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=model.classes_)
    cm_df = pd.DataFrame(cm, index=model.classes_, columns=model.classes_)
    print("\nConfusion Matrix (Sensor Model):")
    print(cm_df)

def evaluate_cnn_model():
    print("\n" + "="*50)
    print("2. CNN IMAGE MODEL EVALUATION (MobileNetV2)")
    print("="*50)
    
    dataset_dir = os.path.join(BASE_DIR, "cnn_dataset")
    if not os.path.exists(dataset_dir):
        print("CNN dataset not found. Run train_cnn.py first.")
        return
        
    # Load model
    model_path = os.path.join(BASE_DIR, "new_tomato_cnn.keras")
    model = tf.keras.models.load_model(model_path)
    
    # Load labels
    label_path = os.path.join(BASE_DIR, "new_class_labels.json")
    with open(label_path, 'r') as f:
        labels_map = json.load(f)
    
    from tensorflow.keras.preprocessing.image import ImageDataGenerator
    datagen = ImageDataGenerator(rescale=1./255)
    
    # Evaluation without shuffle so we can match predictions to true labels
    val_gen = datagen.flow_from_directory(
        dataset_dir,
        target_size=(160, 160),
        batch_size=1,
        class_mode='categorical',
        shuffle=False
    )
    
    if val_gen.samples == 0:
        print("No images found for evaluation.")
        return
        
    y_pred_probs = model.predict(val_gen, steps=val_gen.samples)
    y_pred = np.argmax(y_pred_probs, axis=1)
    y_true = val_gen.classes
    
    class_names = list(val_gen.class_indices.keys())
    
    print("\nNote: Because we trained with only 18 images total using heavy augmentation,")
    print("evaluating on those exact same 18 raw images will show how well it learned them.")
    
    print("\n" + classification_report(y_true, y_pred, target_names=class_names))
    
    cm = confusion_matrix(y_true, y_pred)
    cm_df = pd.DataFrame(cm, index=class_names, columns=class_names)
    print("\nConfusion Matrix (CNN Model on raw uploaded images):")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print(cm_df)

if __name__ == "__main__":
    evaluate_sensor_model()
    evaluate_cnn_model()
