import random

class DataGenerator:

    DEFAULT_SIZES = [10, 50, 100, 500, 1000]

    @staticmethod
    def from_manual(user_input: str) -> list:
        try:
            return [int(x.strip()) for x in user_input.split(",")]
        except ValueError:
            raise ValueError("Invalid input!")

    @staticmethod
    def generate_case(case_type: str = "average", sizes: list = None) -> dict:
        if sizes is None:
            sizes = DataGenerator.DEFAULT_SIZES

        inputs = {}

        for n in sizes:
            inputs[n] = {
                "best": DataGenerator.bestCase(n),
                "average": DataGenerator.averageCase(n),
                "worst": DataGenerator.worstCase(n)
            }

        return inputs

    @staticmethod
    def bestCase(n: int) -> list:
        return list(range(n))

    @staticmethod
    def averageCase(n: int) -> list:
        arr = list(range(n))
        random.shuffle(arr)
        return arr

    @staticmethod
    def worstCase(n: int) -> list:
        return list(range(n, 0, -1))