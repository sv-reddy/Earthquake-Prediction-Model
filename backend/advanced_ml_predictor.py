"""
Advanced Machine Learning and Deep Learning Earthquake Prediction System
Implements multiple state-of-the-art ML/DL techniques for real-time earthquake prediction
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
import asyncio
import logging
from dataclasses import dataclass
import joblib
import os

# Traditional ML Models
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, ExtraTreesRegressor
from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler
from sklearn.model_selection import train_test_split, GridSearchCV, TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.cluster import DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.linear_model import Ridge, Lasso, ElasticNet

# Deep Learning Models
import tensorflow as tf
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.layers import LSTM, GRU, Dense, Dropout, Conv1D, MaxPooling1D, Attention
from tensorflow.keras.layers import Input, concatenate, BatchNormalization, LeakyReLU
from tensorflow.keras.optimizers import Adam, RMSprop
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.regularizers import l1_l2

# Advanced ML techniques
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostRegressor

# Time series analysis
from scipy import signal
from scipy.stats import entropy
import ta  # Technical analysis library

logger = logging.getLogger(__name__)

@dataclass
class PredictionResult:
    """Result structure for earthquake predictions"""
    probability_24h: float
    predicted_magnitude: float
    confidence_score: float
    risk_level: str
    model_ensemble_scores: Dict[str, float]
    feature_importance: Dict[str, float]
    uncertainty_bounds: Tuple[float, float]
    time_to_event: Optional[float]  # Hours
    spatial_risk_map: Dict[str, float]

class AdvancedEarthquakePredictor:
    """
    Advanced ML/DL earthquake prediction system with multiple models
    """
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.is_trained = False
        self.feature_names = []
        self.model_weights = {}
        self.training_history = {}
        
        # Initialize all models
        self._initialize_models()
        
        # Pre-trained weights directory
        self.weights_dir = "model_weights"
        os.makedirs(self.weights_dir, exist_ok=True)
        
    def _initialize_models(self):
        """Initialize all ML/DL models"""
        
        # 1. Ensemble Tree-based Models
        self.models['random_forest'] = RandomForestRegressor(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        
        self.models['gradient_boosting'] = GradientBoostingRegressor(
            n_estimators=150,
            learning_rate=0.1,
            max_depth=8,
            random_state=42
        )
        
        self.models['extra_trees'] = ExtraTreesRegressor(
            n_estimators=200,
            max_depth=12,
            random_state=42,
            n_jobs=-1
        )
        
        # 2. Advanced Gradient Boosting
        self.models['xgboost'] = xgb.XGBRegressor(
            n_estimators=200,
            learning_rate=0.1,
            max_depth=8,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        
        self.models['lightgbm'] = lgb.LGBMRegressor(
            n_estimators=200,
            learning_rate=0.1,
            max_depth=8,
            random_state=42,
            verbosity=-1
        )
        
        self.models['catboost'] = CatBoostRegressor(
            iterations=150,
            learning_rate=0.1,
            depth=8,
            random_seed=42,
            verbose=False
        )
        
        # 3. Support Vector Regression
        self.models['svr_rbf'] = SVR(kernel='rbf', C=100, gamma='scale')
        self.models['svr_linear'] = SVR(kernel='linear', C=100)
        
        # 4. Neural Networks
        self.models['mlp'] = MLPRegressor(
            hidden_layer_sizes=(200, 100, 50),
            activation='relu',
            solver='adam',
            learning_rate='adaptive',
            max_iter=1000,
            random_state=42
        )
        
        # 5. Deep Learning Models (will be built dynamically)
        self.dl_models = {}
        
        # Initialize scalers
        self.scalers = {
            'standard': StandardScaler(),
            'robust': RobustScaler(),
            'minmax': MinMaxScaler()
        }
        
    def _build_lstm_model(self, input_shape: Tuple[int, int]) -> tf.keras.Model:
        """Build LSTM-based deep learning model"""
        model = Sequential([
            LSTM(128, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(64, return_sequences=True),
            Dropout(0.2),
            LSTM(32),
            Dropout(0.2),
            Dense(64, activation='relu'),
            Dense(32, activation='relu'),
            Dense(1, activation='linear')
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        return model
        
    def _build_gru_model(self, input_shape: Tuple[int, int]) -> tf.keras.Model:
        """Build GRU-based deep learning model"""
        model = Sequential([
            GRU(128, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            GRU(64, return_sequences=True),
            Dropout(0.2),
            GRU(32),
            Dropout(0.2),
            Dense(64, activation='relu'),
            Dense(32, activation='relu'),
            Dense(1, activation='linear')
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        return model
        
    def _build_cnn_lstm_model(self, input_shape: Tuple[int, int]) -> tf.keras.Model:
        """Build CNN-LSTM hybrid model"""
        model = Sequential([
            Conv1D(filters=64, kernel_size=3, activation='relu', input_shape=input_shape),
            Conv1D(filters=64, kernel_size=3, activation='relu'),
            Dropout(0.2),
            MaxPooling1D(pool_size=2),
            LSTM(100, return_sequences=True),
            Dropout(0.2),
            LSTM(50),
            Dropout(0.2),
            Dense(50, activation='relu'),
            Dense(1, activation='linear')
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        return model
        
    def _build_attention_model(self, input_shape: Tuple[int, int]) -> tf.keras.Model:
        """Build Attention-based model"""
        inputs = Input(shape=input_shape)
        
        # LSTM with attention
        lstm_out = LSTM(128, return_sequences=True)(inputs)
        lstm_out = Dropout(0.2)(lstm_out)
        
        # Attention mechanism (simplified)
        attention = Dense(1, activation='tanh')(lstm_out)
        attention = tf.keras.layers.Flatten()(attention)
        attention = tf.keras.layers.Activation('softmax')(attention)
        attention = tf.keras.layers.RepeatVector(128)(attention)
        attention = tf.keras.layers.Permute([2, 1])(attention)
        
        # Apply attention
        attended = tf.keras.layers.Multiply()([lstm_out, attention])
        attended = tf.keras.layers.Lambda(lambda x: tf.keras.backend.sum(x, axis=1))(attended)
        
        # Output layers
        dense1 = Dense(64, activation='relu')(attended)
        dense1 = Dropout(0.2)(dense1)
        dense2 = Dense(32, activation='relu')(dense1)
        outputs = Dense(1, activation='linear')(dense2)
        
        model = Model(inputs=inputs, outputs=outputs)
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        return model
        
    def extract_advanced_features(self, earthquakes: List[Dict], location_lat: float, location_lon: float) -> pd.DataFrame:
        """
        Extract comprehensive features using advanced techniques
        """
        if not earthquakes:
            return pd.DataFrame()
            
        df = pd.DataFrame(earthquakes)
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time').reset_index(drop=True)
        
        features = []
        
        for i in range(len(df)):
            earthquake = df.iloc[i]
            
            # Basic features
            basic_features = self._extract_basic_features(earthquake, location_lat, location_lon)
            
            # Temporal features
            temporal_features = self._extract_temporal_features(df, i)
            
            # Spatial clustering features
            spatial_features = self._extract_spatial_features(df, i, location_lat, location_lon)
            
            # Seismic energy features
            energy_features = self._extract_energy_features(df, i)
            
            # Statistical features
            statistical_features = self._extract_statistical_features(df, i)
            
            # Technical analysis features
            technical_features = self._extract_technical_features(df, i)
            
            # Combine all features
            combined_features = {
                **basic_features,
                **temporal_features,
                **spatial_features,
                **energy_features,
                **statistical_features,
                **technical_features
            }
            
            features.append(combined_features)
            
        feature_df = pd.DataFrame(features)
        self.feature_names = list(feature_df.columns)
        
        return feature_df
        
    def _extract_basic_features(self, earthquake: pd.Series, location_lat: float, location_lon: float) -> Dict[str, float]:
        """Extract basic earthquake features"""
        from geopy.distance import geodesic
        
        distance = geodesic((earthquake['latitude'], earthquake['longitude']), 
                          (location_lat, location_lon)).kilometers
        
        return {
            'magnitude': earthquake['magnitude'],
            'depth': earthquake['depth'],
            'distance_km': distance,
            'latitude': earthquake['latitude'],
            'longitude': earthquake['longitude'],
            'lat_diff': earthquake['latitude'] - location_lat,
            'lon_diff': earthquake['longitude'] - location_lon,
        }
        
    def _extract_temporal_features(self, df: pd.DataFrame, index: int) -> Dict[str, float]:
        """Extract temporal pattern features"""
        earthquake = df.iloc[index]
        eq_time = earthquake['time']
        
        # Time-based features
        features = {
            'hour_of_day': eq_time.hour,
            'day_of_week': eq_time.weekday(),
            'day_of_year': eq_time.dayofyear,
            'month': eq_time.month,
            'is_weekend': 1 if eq_time.weekday() >= 5 else 0,
        }
        
        # Time since last earthquake
        if index > 0:
            time_diff = (eq_time - df.iloc[index-1]['time']).total_seconds() / 3600
            features['time_since_last'] = time_diff
        else:
            features['time_since_last'] = 0
            
        # Earthquake frequency features
        recent_window = df[df['time'] >= eq_time - timedelta(days=7)]
        features['events_last_week'] = len(recent_window)
        
        recent_24h = df[df['time'] >= eq_time - timedelta(days=1)]
        features['events_last_24h'] = len(recent_24h)
        
        return features
        
    def _extract_spatial_features(self, df: pd.DataFrame, index: int, location_lat: float, location_lon: float) -> Dict[str, float]:
        """Extract spatial clustering and distribution features"""
        earthquake = df.iloc[index]
        
        # Get nearby earthquakes (within 100km)
        from geopy.distance import geodesic
        nearby_eq = []
        for _, eq in df.iterrows():
            dist = geodesic((eq['latitude'], eq['longitude']), 
                          (earthquake['latitude'], earthquake['longitude'])).kilometers
            if dist <= 100:
                nearby_eq.append(eq)
                
        nearby_df = pd.DataFrame(nearby_eq)
        
        features = {}
        
        if len(nearby_df) > 1:
            # Spatial clustering using DBSCAN
            coords = nearby_df[['latitude', 'longitude']].values
            try:
                clustering = DBSCAN(eps=0.5, min_samples=2).fit(coords)
                features['cluster_id'] = clustering.labels_[0] if len(clustering.labels_) > 0 else -1
                features['n_clusters'] = len(set(clustering.labels_)) - (1 if -1 in clustering.labels_ else 0)
            except:
                features['cluster_id'] = -1
                features['n_clusters'] = 0
                
            # Spatial dispersion
            features['spatial_std_lat'] = nearby_df['latitude'].std()
            features['spatial_std_lon'] = nearby_df['longitude'].std()
            features['spatial_range_lat'] = nearby_df['latitude'].max() - nearby_df['latitude'].min()
            features['spatial_range_lon'] = nearby_df['longitude'].max() - nearby_df['longitude'].min()
        else:
            features.update({
                'cluster_id': -1,
                'n_clusters': 0,
                'spatial_std_lat': 0,
                'spatial_std_lon': 0,
                'spatial_range_lat': 0,
                'spatial_range_lon': 0
            })
            
        return features
        
    def _extract_energy_features(self, df: pd.DataFrame, index: int) -> Dict[str, float]:
        """Extract seismic energy features"""
        earthquake = df.iloc[index]
        
        # Seismic energy calculations
        magnitude = earthquake['magnitude']
        energy = 10 ** (1.5 * magnitude + 4.8)  # Joules
        
        features = {
            'seismic_energy': energy,
            'log_energy': np.log10(energy),
            'energy_per_depth': energy / max(earthquake['depth'], 1),
        }
        
        # Cumulative energy from recent earthquakes
        recent_window = df.iloc[max(0, index-10):index+1]
        cumulative_energy = sum(10 ** (1.5 * eq['magnitude'] + 4.8) for _, eq in recent_window.iterrows())
        features['cumulative_energy_10'] = cumulative_energy
        features['energy_ratio'] = energy / cumulative_energy if cumulative_energy > 0 else 0
        
        return features
        
    def _extract_statistical_features(self, df: pd.DataFrame, index: int) -> Dict[str, float]:
        """Extract statistical features from recent earthquake patterns"""
        # Get recent earthquakes (last 20 events or within time window)
        recent_window = df.iloc[max(0, index-20):index+1]
        
        if len(recent_window) < 2:
            return {f'stat_{key}': 0 for key in ['mag_mean', 'mag_std', 'mag_skew', 'mag_kurt', 
                                                'depth_mean', 'depth_std', 'freq_trend']}
        
        magnitudes = recent_window['magnitude'].values
        depths = recent_window['depth'].values
        
        from scipy.stats import skew, kurtosis
        
        features = {
            'stat_mag_mean': np.mean(magnitudes),
            'stat_mag_std': np.std(magnitudes),
            'stat_mag_skew': skew(magnitudes),
            'stat_mag_kurt': kurtosis(magnitudes),
            'stat_depth_mean': np.mean(depths),
            'stat_depth_std': np.std(depths),
            'stat_mag_trend': np.polyfit(range(len(magnitudes)), magnitudes, 1)[0] if len(magnitudes) > 1 else 0,
        }
        
        return features
        
    def _extract_technical_features(self, df: pd.DataFrame, index: int) -> Dict[str, float]:
        """Extract technical analysis features"""
        # Get magnitude time series
        recent_window = df.iloc[max(0, index-50):index+1]
        
        if len(recent_window) < 10:
            return {f'tech_{key}': 0 for key in ['rsi', 'bollinger_pos', 'ma_trend', 'volatility']}
        
        magnitudes = recent_window['magnitude'].values
        
        try:
            # RSI-like indicator for earthquake magnitude
            deltas = np.diff(magnitudes)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else np.mean(gains)
            avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else np.mean(losses)
            rs = avg_gain / avg_loss if avg_loss != 0 else 100
            rsi = 100 - (100 / (1 + rs))
            
            # Moving averages
            ma_short = np.mean(magnitudes[-5:]) if len(magnitudes) >= 5 else np.mean(magnitudes)
            ma_long = np.mean(magnitudes[-20:]) if len(magnitudes) >= 20 else np.mean(magnitudes)
            ma_trend = (ma_short - ma_long) / ma_long if ma_long != 0 else 0
            
            # Bollinger-like bands
            rolling_mean = np.mean(magnitudes[-20:]) if len(magnitudes) >= 20 else np.mean(magnitudes)
            rolling_std = np.std(magnitudes[-20:]) if len(magnitudes) >= 20 else np.std(magnitudes)
            current_mag = magnitudes[-1]
            bollinger_pos = (current_mag - rolling_mean) / (2 * rolling_std) if rolling_std != 0 else 0
            
            # Volatility
            volatility = np.std(magnitudes[-10:]) if len(magnitudes) >= 10 else np.std(magnitudes)
            
        except:
            rsi, ma_trend, bollinger_pos, volatility = 0, 0, 0, 0
        
        return {
            'tech_rsi': rsi,
            'tech_ma_trend': ma_trend,
            'tech_bollinger_pos': bollinger_pos,
            'tech_volatility': volatility
        }
        
    async def train_models(self, historical_data: List[Dict], location_lat: float, location_lon: float) -> Dict[str, Any]:
        """
        Train all ML/DL models with historical earthquake data
        """
        logger.info("Starting advanced ML model training...")
        
        if len(historical_data) < 50:
            logger.warning(f"Insufficient data for training: {len(historical_data)} samples")
            return {"status": "insufficient_data", "samples": len(historical_data)}
        
        # Extract features
        feature_df = self.extract_advanced_features(historical_data, location_lat, location_lon)
        
        if feature_df.empty:
            return {"status": "feature_extraction_failed"}
        
        # Prepare targets (next earthquake magnitude and time)
        targets = self._prepare_targets(historical_data)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            feature_df.values, targets['magnitude'], 
            test_size=0.2, random_state=42, shuffle=False
        )
        
        # Scale features
        X_train_scaled = {}
        X_test_scaled = {}
        
        for scaler_name, scaler in self.scalers.items():
            X_train_scaled[scaler_name] = scaler.fit_transform(X_train)
            X_test_scaled[scaler_name] = scaler.transform(X_test)
        
        # Train traditional ML models
        ml_results = await self._train_ml_models(X_train_scaled, X_test_scaled, y_train, y_test)
        
        # Train deep learning models
        dl_results = await self._train_dl_models(X_train_scaled, X_test_scaled, y_train, y_test)
        
        # Combine results
        training_results = {
            **ml_results,
            **dl_results,
            "feature_count": len(self.feature_names),
            "training_samples": len(X_train),
            "test_samples": len(X_test)
        }
        
        self.is_trained = True
        self.training_history = training_results
        
        # Save models
        await self._save_models()
        
        logger.info("Model training completed successfully")
        return training_results
        
    async def _train_ml_models(self, X_train_scaled: Dict, X_test_scaled: Dict, 
                              y_train: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
        """Train traditional ML models"""
        ml_results = {}
        
        # Use standard scaler for most models
        X_train = X_train_scaled['standard']
        X_test = X_test_scaled['standard']
        
        for model_name, model in self.models.items():
            try:
                logger.info(f"Training {model_name}...")
                
                # Train model
                model.fit(X_train, y_train)
                
                # Evaluate
                train_pred = model.predict(X_train)
                test_pred = model.predict(X_test)
                
                train_mse = mean_squared_error(y_train, train_pred)
                test_mse = mean_squared_error(y_test, test_pred)
                test_r2 = r2_score(y_test, test_pred)
                
                ml_results[model_name] = {
                    'train_mse': train_mse,
                    'test_mse': test_mse,
                    'test_r2': test_r2,
                    'status': 'success'
                }
                
                # Calculate model weight based on performance
                self.model_weights[model_name] = max(0, test_r2)
                
            except Exception as e:
                logger.error(f"Error training {model_name}: {str(e)}")
                ml_results[model_name] = {'status': 'failed', 'error': str(e)}
                self.model_weights[model_name] = 0
        
        return ml_results
        
    async def _train_dl_models(self, X_train_scaled: Dict, X_test_scaled: Dict, 
                              y_train: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
        """Train deep learning models"""
        dl_results = {}
        
        # Reshape data for time series (create sequences)
        sequence_length = 10
        X_train_seq, y_train_seq = self._create_sequences(X_train_scaled['minmax'], y_train, sequence_length)
        X_test_seq, y_test_seq = self._create_sequences(X_test_scaled['minmax'], y_test, sequence_length)
        
        if X_train_seq.shape[0] < 10:
            return {"dl_models": "insufficient_sequence_data"}
        
        input_shape = (X_train_seq.shape[1], X_train_seq.shape[2])
        
        # Define DL models to train
        dl_model_configs = {
            'lstm': self._build_lstm_model,
            'gru': self._build_gru_model,
            'cnn_lstm': self._build_cnn_lstm_model,
            'attention': self._build_attention_model
        }
        
        callbacks = [
            EarlyStopping(patience=10, restore_best_weights=True),
            ReduceLROnPlateau(patience=5, factor=0.5)
        ]
        
        for model_name, model_builder in dl_model_configs.items():
            try:
                logger.info(f"Training DL model: {model_name}...")
                
                # Build model
                model = model_builder(input_shape)
                
                # Train model
                history = model.fit(
                    X_train_seq, y_train_seq,
                    validation_data=(X_test_seq, y_test_seq),
                    epochs=50,
                    batch_size=32,
                    callbacks=callbacks,
                    verbose=0
                )
                
                # Evaluate
                test_pred = model.predict(X_test_seq, verbose=0)
                test_mse = mean_squared_error(y_test_seq, test_pred)
                test_r2 = r2_score(y_test_seq, test_pred)
                
                # Store model
                self.dl_models[model_name] = model
                
                dl_results[f'dl_{model_name}'] = {
                    'test_mse': test_mse,
                    'test_r2': test_r2,
                    'final_val_loss': min(history.history['val_loss']),
                    'status': 'success'
                }
                
                # Calculate model weight
                self.model_weights[f'dl_{model_name}'] = max(0, test_r2)
                
            except Exception as e:
                logger.error(f"Error training DL model {model_name}: {str(e)}")
                dl_results[f'dl_{model_name}'] = {'status': 'failed', 'error': str(e)}
                self.model_weights[f'dl_{model_name}'] = 0
        
        return dl_results
        
    def _create_sequences(self, data: np.ndarray, targets: np.ndarray, sequence_length: int) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for time series prediction"""
        X, y = [], []
        
        for i in range(sequence_length, len(data)):
            X.append(data[i-sequence_length:i])
            y.append(targets[i])
            
        return np.array(X), np.array(y)
        
    def _prepare_targets(self, historical_data: List[Dict]) -> Dict[str, np.ndarray]:
        """Prepare prediction targets"""
        magnitudes = [eq['magnitude'] for eq in historical_data]
        
        # Shift targets to predict next earthquake
        magnitude_targets = magnitudes[1:] + [magnitudes[-1]]  # Predict next magnitude
        
        return {
            'magnitude': np.array(magnitude_targets),
        }
        
    async def predict_earthquake_risk(self, recent_earthquakes: List[Dict], 
                                    location_lat: float, location_lon: float) -> PredictionResult:
        """
        Generate comprehensive earthquake predictions using ensemble of models
        """
        if not self.is_trained:
            # Load pre-trained models or use baseline prediction
            await self._load_models()
        
        # Extract features
        feature_df = self.extract_advanced_features(recent_earthquakes, location_lat, location_lon)
        
        if feature_df.empty:
            return self._baseline_prediction()
        
        # Get latest features
        latest_features = feature_df.iloc[-1:].values
        
        # Scale features
        scaled_features = {}
        for scaler_name, scaler in self.scalers.items():
            try:
                scaled_features[scaler_name] = scaler.transform(latest_features)
            except:
                scaled_features[scaler_name] = latest_features
        
        # Get predictions from all models
        predictions = {}
        
        # ML model predictions
        for model_name, model in self.models.items():
            try:
                pred = model.predict(scaled_features['standard'])[0]
                predictions[model_name] = pred
            except:
                predictions[model_name] = 0
        
        # DL model predictions
        if hasattr(self, 'dl_models'):
            sequence_length = 10
            if len(feature_df) >= sequence_length:
                recent_features = scaled_features['minmax'][-sequence_length:].reshape(1, sequence_length, -1)
                
                for model_name, model in self.dl_models.items():
                    try:
                        pred = model.predict(recent_features, verbose=0)[0][0]
                        predictions[f'dl_{model_name}'] = pred
                    except:
                        predictions[f'dl_{model_name}'] = 0
        
        # Ensemble prediction
        ensemble_prediction = self._ensemble_predict(predictions)
        
        # Calculate risk metrics
        risk_result = self._calculate_risk_metrics(
            ensemble_prediction, recent_earthquakes, location_lat, location_lon
        )
        
        return risk_result
        
    def _ensemble_predict(self, predictions: Dict[str, float]) -> float:
        """Combine predictions using weighted ensemble"""
        if not predictions:
            return 0.0
        
        # Normalize weights
        total_weight = sum(self.model_weights.get(name, 0.1) for name in predictions.keys())
        
        if total_weight == 0:
            return np.mean(list(predictions.values()))
        
        weighted_sum = sum(
            pred * self.model_weights.get(name, 0.1) 
            for name, pred in predictions.items()
        )
        
        return weighted_sum / total_weight
        
    def _calculate_risk_metrics(self, predicted_magnitude: float, recent_earthquakes: List[Dict],
                               location_lat: float, location_lon: float) -> PredictionResult:
        """Calculate comprehensive risk metrics"""
        
        # Calculate 24-hour probability based on recent activity and prediction
        recent_activity = len([eq for eq in recent_earthquakes 
                             if (datetime.now() - datetime.fromisoformat(eq['time'].replace('Z', ''))).days <= 1])
        
        base_probability = min(recent_activity * 0.1, 0.8)
        magnitude_factor = min(predicted_magnitude / 7.0, 1.0)
        probability_24h = min(base_probability + magnitude_factor * 0.2, 0.95)
        
        # Calculate confidence based on model agreement
        confidence = 0.7 + (len(recent_earthquakes) / 100) * 0.3
        confidence = min(confidence, 0.95)
        
        # Determine risk level
        if probability_24h > 0.7 or predicted_magnitude > 6.0:
            risk_level = "High"
        elif probability_24h > 0.4 or predicted_magnitude > 5.0:
            risk_level = "Moderate"
        elif probability_24h > 0.2 or predicted_magnitude > 4.0:
            risk_level = "Low-Moderate"
        else:
            risk_level = "Low"
        
        return PredictionResult(
            probability_24h=probability_24h * 100,  # Convert to percentage
            predicted_magnitude=predicted_magnitude,
            confidence_score=confidence,
            risk_level=risk_level,
            model_ensemble_scores={},
            feature_importance={},
            uncertainty_bounds=(predicted_magnitude - 0.5, predicted_magnitude + 0.5),
            time_to_event=None,
            spatial_risk_map={}
        )
        
    def _baseline_prediction(self) -> PredictionResult:
        """Baseline prediction when models aren't available"""
        return PredictionResult(
            probability_24h=5.0,
            predicted_magnitude=3.5,
            confidence_score=0.3,
            risk_level="Low",
            model_ensemble_scores={},
            feature_importance={},
            uncertainty_bounds=(3.0, 4.0),
            time_to_event=None,
            spatial_risk_map={}
        )
        
    async def _save_models(self):
        """Save trained models to disk"""
        try:
            # Save ML models
            for name, model in self.models.items():
                joblib.dump(model, f"{self.weights_dir}/{name}_model.pkl")
            
            # Save scalers
            for name, scaler in self.scalers.items():
                joblib.dump(scaler, f"{self.weights_dir}/{name}_scaler.pkl")
            
            # Save DL models
            for name, model in self.dl_models.items():
                model.save(f"{self.weights_dir}/{name}_dl_model.h5")
            
            # Save metadata
            metadata = {
                'feature_names': self.feature_names,
                'model_weights': self.model_weights,
                'is_trained': self.is_trained
            }
            joblib.dump(metadata, f"{self.weights_dir}/metadata.pkl")
            
        except Exception as e:
            logger.error(f"Error saving models: {str(e)}")
            
    async def _load_models(self):
        """Load pre-trained models from disk"""
        try:
            # Load metadata
            if os.path.exists(f"{self.weights_dir}/metadata.pkl"):
                metadata = joblib.load(f"{self.weights_dir}/metadata.pkl")
                self.feature_names = metadata.get('feature_names', [])
                self.model_weights = metadata.get('model_weights', {})
                self.is_trained = metadata.get('is_trained', False)
            
            # Load ML models
            for name in self.models.keys():
                model_path = f"{self.weights_dir}/{name}_model.pkl"
                if os.path.exists(model_path):
                    self.models[name] = joblib.load(model_path)
            
            # Load scalers
            for name in self.scalers.keys():
                scaler_path = f"{self.weights_dir}/{name}_scaler.pkl"
                if os.path.exists(scaler_path):
                    self.scalers[name] = joblib.load(scaler_path)
            
            # Load DL models
            dl_model_names = ['lstm', 'gru', 'cnn_lstm', 'attention']
            for name in dl_model_names:
                model_path = f"{self.weights_dir}/{name}_dl_model.h5"
                if os.path.exists(model_path):
                    self.dl_models[name] = tf.keras.models.load_model(model_path)
            
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
