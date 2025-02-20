import numpy as np


def ca(img: np.ndarray, train_hs: int, guard_hs: int, tau: float) -> np.ndarray:
    ret = np.zeros_like(img, dtype=np.uint8)

    for col in range(img.shape[1]):
        for row in range(train_hs + guard_hs, img.shape[0] - train_hs - guard_hs):
            sum_train = 0
            for i in range(row - train_hs - guard_hs, row + train_hs + guard_hs + 1):
                if abs(i - row) > guard_hs:
                    sum_train += img[i, col]
            ret[row, col] = img[row, col] > tau * sum_train / (2.0 * train_hs)

    return ret


def soca(img: np.ndarray, train_hs: int, guard_hs: int, tau: float) -> np.ndarray:
    ret = np.zeros_like(img, dtype=np.uint8)

    for col in range(img.shape[1]):
        for row in range(train_hs + guard_hs, img.shape[0] - train_hs - guard_hs):
            leading_sum, lagging_sum = 0.0, 0.0
            for i in range(row - train_hs - guard_hs, row + train_hs + guard_hs + 1):
                if (i - row) > guard_hs:
                    lagging_sum += img[i, col]
                elif (i - row) < -guard_hs:
                    leading_sum += img[i, col]
            sum_train = min(leading_sum, lagging_sum)
            ret[row, col] = img[row, col] > tau * sum_train / train_hs

    return ret


def goca(img: np.ndarray, train_hs: int, guard_hs: int, tau: float) -> np.ndarray:
    ret = np.zeros_like(img, dtype=np.uint8)

    for col in range(img.shape[1]):
        for row in range(train_hs + guard_hs, img.shape[0] - train_hs - guard_hs):
            leading_sum, lagging_sum = 0.0, 0.0
            for i in range(row - train_hs - guard_hs, row + train_hs + guard_hs + 1):
                if (i - row) > guard_hs:
                    lagging_sum += img[i, col]
                elif (i - row) < -guard_hs:
                    leading_sum += img[i, col]
            sum_train = max(leading_sum, lagging_sum)
            ret[row, col] = img[row, col] > tau * sum_train / train_hs

    return ret


def os(img: np.ndarray, train_hs: int, guard_hs: int, k: int, tau: float) -> np.ndarray:
    ret = np.zeros_like(img, dtype=np.uint8)

    for col in range(img.shape[1]):
        for row in range(train_hs + guard_hs, img.shape[0] - train_hs - guard_hs):
            train = []
            for i in range(row - train_hs - guard_hs, row + train_hs + guard_hs + 1):
                if abs(i - row) > guard_hs:
                    train.append(img[i, col])
            train = np.array(train)
            kth_value = np.partition(train, k)[k]
            ret[row, col] = img[row, col] > tau * kth_value

    return ret


def ca2(img: np.ndarray, train_hs: int, guard_hs: int, tau: float):
    ret = np.zeros_like(img, dtype=np.uint8)
    ret2 = np.zeros_like(img, dtype=np.float32)

    for col in range(img.shape[1]):
        for row in range(train_hs + guard_hs, img.shape[0] - train_hs - guard_hs):
            sum_train = 0
            for i in range(row - train_hs - guard_hs, row + train_hs + guard_hs + 1):
                if abs(i - row) > guard_hs:
                    sum_train += img[i, col]
            ret[row, col] = img[row, col] > tau * sum_train / (2.0 * train_hs)
            ret2[row, col] = tau * sum_train / (2.0 * train_hs)

    return ret, ret2


def soca2(img: np.ndarray, train_hs: int, guard_hs: int, tau: float):
    ret = np.zeros_like(img, dtype=np.uint8)
    ret2 = np.zeros_like(img, dtype=np.float32)

    for col in range(img.shape[1]):
        for row in range(train_hs + guard_hs, img.shape[0] - train_hs - guard_hs):
            leading_sum, lagging_sum = 0.0, 0.0
            for i in range(row - train_hs - guard_hs, row + train_hs + guard_hs + 1):
                if (i - row) > guard_hs:
                    lagging_sum += img[i, col]
                elif (i - row) < -guard_hs:
                    leading_sum += img[i, col]
            sum_train = min(leading_sum, lagging_sum)
            ret[row, col] = img[row, col] > tau * sum_train / train_hs
            ret2[row, col] = tau * sum_train / train_hs

    return ret, ret2


def goca2(img: np.ndarray, train_hs: int, guard_hs: int, tau: float):
    ret = np.zeros_like(img, dtype=np.uint8)
    ret2 = np.zeros_like(img, dtype=np.float32)

    for col in range(img.shape[1]):
        for row in range(train_hs + guard_hs, img.shape[0] - train_hs - guard_hs):
            leading_sum, lagging_sum = 0.0, 0.0
            for i in range(row - train_hs - guard_hs, row + train_hs + guard_hs + 1):
                if (i - row) > guard_hs:
                    lagging_sum += img[i, col]
                elif (i - row) < -guard_hs:
                    leading_sum += img[i, col]
            sum_train = max(leading_sum, lagging_sum)
            ret[row, col] = img[row, col] > tau * sum_train / train_hs
            ret2[row, col] = tau * sum_train / train_hs

    return ret, ret2


def os2(img: np.ndarray, train_hs: int, guard_hs: int, k: int, tau: float):
    ret = np.zeros_like(img, dtype=np.uint8)
    ret2 = np.zeros_like(img, dtype=np.float32)

    for col in range(img.shape[1]):
        for row in range(train_hs + guard_hs, img.shape[0] - train_hs - guard_hs):
            train = []
            for i in range(row - train_hs - guard_hs, row + train_hs + guard_hs + 1):
                if abs(i - row) > guard_hs:
                    train.append(img[i, col])
            train = np.array(train)
            kth_value = np.partition(train, k)[k]
            ret[row, col] = img[row, col] > tau * kth_value
            ret2[row, col] = tau * kth_value

    return ret, ret2
