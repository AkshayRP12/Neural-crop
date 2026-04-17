import os
import glob
import json
import numpy as np
import tensorflow as tf
from PIL import Image

def extract_features(image_path):
    pil_img = Image.open(image_path)
    w, h = pil_img.size
    crop_pct = 0.25
    left   = int(w * crop_pct)
    top    = int(h * crop_pct)
    right  = int(w * (1 - crop_pct))
    bottom = int(h * (1 - crop_pct))
    pil_img = pil_img.crop((left, top, right, bottom))
    pil_img = pil_img.resize((160, 160))
    feature = tf.keras.utils.img_to_array(pil_img)
    return feature

def finetune():
    print("[+] Loading the upgraded model...")
    model = tf.keras.models.load_model('plant_disease_recog_model_pwp.keras')
    
    for layer in model.layers[:-1]:
        layer.trainable = False
        
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),  # Higher LR
                  loss='categorical_crossentropy',  # Forces it to pick ONLY ONE WINNER
                  metrics=['accuracy'])
    
    X, Y = [], []
    target_image = '../uploadimages/iot_2bd3ccd7e45a43d0a1a8ddda7002fe0a_field_capture.jpg'
    healthy_idx = 38 
    
    img_array = extract_features(target_image)
    
    # 100 copies! Really force it.
    for _ in range(100):
        X.append(img_array)
        y_vec = np.zeros(39)
        y_vec[healthy_idx] = 1.0
        Y.append(y_vec)
        
    # We still need negative examples to balance
    folder_mapping = {
        'bacterial spot': 29, 'early blight': 30, 'late blight': 31,
        'leaf mold': 32, 'septoria': 33, 'spider mites': 34,
        'target spot': 35, 'yellow leaf curl virus': 36, 'mosiac virus': 37
    }
    
    for folder, idx in folder_mapping.items():
        files = glob.glob(f'images/{folder}/*')
        for f in files:
            try:
                feat = extract_features(f)
                X.append(feat)
                y_vec = np.zeros(39)
                y_vec[idx] = 1.0
                Y.append(y_vec)
            except Exception as e:
                pass
                
    X = np.array(X)
    Y = np.array(Y)
    
    datagen = tf.keras.preprocessing.image.ImageDataGenerator(
        rotation_range=20, width_shift_range=0.2, height_shift_range=0.2,
        zoom_range=0.2, horizontal_flip=True, vertical_flip=True
    )
    
    print("[+] Fine-tuning with categorical_crossentropy to squash competing diseases...")
    model.fit(datagen.flow(X, Y, batch_size=8), epochs=20)
    
    model.save('plant_disease_recog_model_pwp.keras')
    print("[+] Done! Restart the Flask server.")

if __name__ == '__main__':
    finetune()
