class Calculator:
    def __init__(self):
        self.operators = {
            "+": lambda a, b: a + b,
            "-": lambda a, b: a - b,
            "*": lambda a, b: a * b,
            "/": lambda a, b: a / b,
        }

        self.precedence = {
            "+": 1,
            "-": 1,
            "*": 2,
            "/": 2,
        }


    def evaluate(self, expression):
        if not expression or expression.isspace():
            return None
        tokens = expression.strip().split()
        return self.evaluate_infix(tokens)


    def evaluate_infix(self, tokens):
        values = []
        operator = []

        for token in tokens:
            if token in self.operators:
                while (
                    operator
                    and operator[-1] in self.operators
                    and self.precedence[operator[-1]] >= self.precedence[token]
                ):
                    self._apply_operator(operator, values)
                operator.append(token)

            else:
                try:
                    values.append(float(token))
                except ValueError:
                    raise ValueError(f"invalid token: {token}")

        while operator:
            self._apply_operator(operator, values)

        if len(values) != 1:
            raise ValueError("invalid expression")

        return values[0]

    def _apply_operator(self, operator, values):
        if not operator:
            return

        operator = operator.pop()
        if len(values) < 2:
            raise ValueError(f"not enough operands for operator {operator}")

        b = values.pop()
        a = values.pop()
        values.append(self.operators[operator](a, b))