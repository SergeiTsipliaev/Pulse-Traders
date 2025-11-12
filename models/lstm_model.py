import numpy as np
from sklearn.preprocessing import MinMaxScaler
import logging

logger = logging.getLogger(__name__)


class AdvancedPricePredictor:
    """Продвинутый предсказатель цен с ensemble методами"""

    def __init__(self, sequence_length: int = 60):
        self.sequence_length = sequence_length
        self.scaler = MinMaxScaler(feature_range=(0.1, 0.9))

    def prepare_data(self, prices: np.ndarray) -> np.ndarray:
        """Подготовка и нормализация данных"""
        prices = np.array(prices, dtype=float)

        if np.any(np.isnan(prices)) or np.any(np.isinf(prices)):
            prices = prices[~np.isnan(prices)]
            prices = prices[~np.isinf(prices)]

        if len(prices) == 0:
            raise ValueError("Нет валидных данных")

        prices_normalized = self.scaler.fit_transform(prices.reshape(-1, 1)).flatten()
        return prices_normalized

    def denormalize(self, values: np.ndarray) -> np.ndarray:
        """Денормализация данных"""
        return self.scaler.inverse_transform(values.reshape(-1, 1)).flatten()

    def polynomial_prediction(self, prices: np.ndarray, future_steps: int = 7, degree: int = 3) -> np.ndarray:
        """Полиномиальная регрессия"""
        try:
            x = np.arange(len(prices))
            y = prices

            coeffs = np.polyfit(x, y, degree)
            poly = np.poly1d(coeffs)

            future_x = np.arange(len(prices), len(prices) + future_steps)
            predictions = poly(future_x)

            min_val = np.min(prices)
            max_val = np.max(prices)
            margin = (max_val - min_val) * 0.15
            predictions = np.clip(predictions, min_val - margin, max_val + margin)

            return predictions
        except Exception as e:
            logger.warning(f"Ошибка полинома: {e}")
            return np.array([prices[-1]] * future_steps)

    def exponential_smoothing(self, prices: np.ndarray, future_steps: int = 7, alpha: float = 0.3) -> np.ndarray:
        """Экспоненциальное сглаживание"""
        try:
            s = prices[0]
            trend = prices[1] - prices[0]
            predictions = []

            for i in range(1, len(prices)):
                s_new = alpha * prices[i] + (1 - alpha) * (s + trend)
                trend = 0.2 * (s_new - s) + 0.8 * trend
                s = s_new

            for i in range(future_steps):
                s = s + trend
                trend = trend * 0.95
                predictions.append(s)

            return np.array(predictions)
        except Exception as e:
            logger.warning(f"Ошибка экспоненциального сглаживания: {e}")
            return np.array([prices[-1]] * future_steps)

    def moving_average_prediction(self, prices: np.ndarray, future_steps: int = 7) -> np.ndarray:
        """Прогноз на основе скользящих средних"""
        try:
            ma_short = np.mean(prices[-7:]) if len(prices) >= 7 else np.mean(prices)
            ma_medium = np.mean(prices[-14:]) if len(prices) >= 14 else np.mean(prices)
            ma_long = np.mean(prices[-30:]) if len(prices) >= 30 else np.mean(prices)

            weighted_ma = (ma_short * 0.5 + ma_medium * 0.3 + ma_long * 0.2)
            recent_trend = (prices[-1] - prices[-7]) / max(abs(prices[-7]), 0.001) if len(prices) >= 7 else 0

            predictions = []
            current = weighted_ma

            for i in range(future_steps):
                decay = 0.95 ** (i + 1)
                pred = current + (recent_trend * decay)
                predictions.append(pred)

            return np.array(predictions)
        except Exception as e:
            logger.warning(f"Ошибка MA: {e}")
            return np.array([prices[-1]] * future_steps)

    def linear_regression_trend(self, prices: np.ndarray, future_steps: int = 7) -> np.ndarray:
        """Линейная регрессия с корректировкой"""
        try:
            x = np.arange(len(prices))
            y = prices

            coeffs = np.polyfit(x, y, 1)
            slope = coeffs[0]
            intercept = coeffs[1]

            residuals = y - (slope * x + intercept)
            volatility = np.std(residuals) / np.mean(np.abs(y))

            if volatility > 0.05:
                slope = slope * (1 - volatility)

            future_x = np.arange(len(prices), len(prices) + future_steps)
            predictions = slope * future_x + intercept

            return predictions
        except Exception as e:
            logger.warning(f"Ошибка линейной регрессии: {e}")
            return np.array([prices[-1]] * future_steps)

    def ensemble_prediction(self, prices: np.ndarray, future_steps: int = 7) -> tuple:
        """Ensemble прогноз - комбинирует все методы"""
        try:
            if len(prices) < 10:
                logger.warning("Недостаточно данных")
                return np.array([prices[-1]] * future_steps), 30.0, {}

            prices_norm = self.prepare_data(prices)

            poly_pred = self.polynomial_prediction(prices_norm, future_steps, degree=3)
            exp_pred = self.exponential_smoothing(prices_norm, future_steps)
            ma_pred = self.moving_average_prediction(prices_norm, future_steps)
            linear_pred = self.linear_regression_trend(prices_norm, future_steps)

            poly_denorm = self.denormalize(poly_pred)
            exp_denorm = self.denormalize(exp_pred)
            ma_denorm = self.denormalize(ma_pred)
            linear_denorm = self.denormalize(linear_pred)

            weights = np.array([0.35, 0.25, 0.25, 0.15])

            ensemble_pred = (
                    poly_denorm * weights[0] +
                    exp_denorm * weights[1] +
                    ma_denorm * weights[2] +
                    linear_denorm * weights[3]
            )

            predictions_all = np.array([poly_denorm, exp_denorm, ma_denorm, linear_denorm])
            std_agreement = np.std(predictions_all, axis=0).mean()

            confidence = max(40, 100 - (std_agreement / np.mean(np.abs(prices)) * 500))
            confidence = min(90, confidence)

            method_details = {
                'polynomial': poly_denorm.tolist(),
                'exponential': exp_denorm.tolist(),
                'moving_average': ma_denorm.tolist(),
                'linear': linear_denorm.tolist(),
                'std_agreement': float(std_agreement),
                'weights': weights.tolist()
            }

            return ensemble_pred, confidence, method_details

        except Exception as e:
            logger.error(f"Ошибка ensemble: {e}")
            return np.array([prices[-1]] * future_steps), 30.0, {}


predictor = AdvancedPricePredictor()