import math  # For sqrt, log, sin, cos, etc.
import numpy as np  # For more complex mathematical operations

class WWAA_BasicMathNode:
    """
    A custom math node that performs operations on two inputs (a and b)
    and outputs results as both integer and float
    """
    
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "a": ("INT,FLOAT",),
                "b": ("INT,FLOAT",),
                "operation": (["a+b", "a-b", "b-a", "a*b", "a/b", "b/a", "a%b", "a**b"], {
                    "default": "a+b"
                }),
            },
        }
    
    RETURN_TYPES = ("INT", "FLOAT")
    RETURN_NAMES = ("result_int", "result_float")
    FUNCTION = "calculate"
    CATEGORY = "🪠️ WWAA/math"
    
    def calculate(self, a, b, operation):
        """
        Perform the selected operation and return both int and float results
        """
        # Perform the calculation based on operation
        if operation == "a+b":
            result = a + b
        elif operation == "a-b":
            result = a - b
        elif operation == "b-a":
            result = b - a
        elif operation == "a*b":
            result = a * b
        elif operation == "a/b":
            if b == 0:
                result = 0.0  # Handle division by zero
            else:
                result = a / b
        elif operation == "b/a":
            if a == 0:
                result = 0.0  # Handle division by zero
            else:
                result = b / a
        elif operation == "a%b":
            if b == 0:
                result = 0.0  # Handle modulo by zero
            else:
                result = a % b
        elif operation == "a**b":
            try:
                result = a ** b
            except (OverflowError, ValueError):
                result = 0.0  # Handle overflow or invalid power operations
        else:
            result = 0.0
        
        # Convert to int and float
        result_int = int(result)
        result_float = float(result)
        
        return (result_int, result_float)