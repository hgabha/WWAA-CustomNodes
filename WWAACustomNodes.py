import math, string, re

debug = False

class WWAA_LineCount:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "string_text": ("STRING", {
                    "multiline": True,
                    "default":"String goes here\nSecond line."
                }),
                

            },
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("Line Count",)

    FUNCTION = "executeLineCount"
    CATEGORY = "🪠️WWAA"
    
    def executeLineCount(self, string_text):
        #count lines
        string_text = string_text.strip() #strip extra line feeds
        string_text = string_text.strip()
        string_text = re.sub(r'((\n){2,})', '\n', string_text)
        lines = string_text.split('\n')
        print(lines if debug else "")
        num_lines = len(lines)
        print(num_lines if debug else "")
        return (num_lines,)

class WWAA_BuildString:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "pre_text": ("STRING", {
                    "multiline": False,
                    "default":"Pre-text"
                }),
                "input_text": ("STRING", {
                    "forceInput": True,
                }),
                "post_text": ("STRING", {
                    "multiline": False,
                    "default":"Post-text"
                }),

            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("Joined String",)

    FUNCTION = "executeBuildString"
    CATEGORY = "🪠️WWAA"
    
    def executeBuildString(self, pre_text, input_text, post_text):
        #Concatenate and build string
        joinString = pre_text + input_text + post_text
        print(joinString if debug else "")
        return (joinString,)
        
        
# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
WWAA_CLASS_MAPPINGS = {
    "WWAA-LineCount": WWAA_LineCount,
    "WWAA-BuildString": WWAA_BuildString,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
WWAA_DISPLAY_NAME_MAPPINGS = {
    "WWAA-LineCount": "🪠️ WWAA LineCount",
    "WWAA-BuildString": "🪠️ WWAA JoinString",
}
