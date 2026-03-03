# WWAA-CustomNodes
Custom Nodes for ComfyUI made by the team at [WeirdWonderfulAI.Art](https://weirdwonderfulai.art)
These are developed based on the needs where there was a gap to make our workflows better. You are welcome to use it as you see fit.

[![logo](https://weirdwonderfulai.art/wp-content/uploads/2022/01/WWAA_web_logo.jpg "WeirdWonderfulAI.Art")](https://weirdwonderfulai.art)

## List of Custom Nodes
- [Line Count](#line-count)
- [Image Batch Loader](#image-batch-loader)
- [Image Dimension Calculator](#image-dimension-calculator)
- [Image Dimension Size](#image-dimension-size)

## Line Count
Custom node that takes a string list as input and will output text lines found within as Integer. It will remove blank lines from the final count.
![wwaa-Line-count](https://github.com/user-attachments/assets/9117cc3f-63ed-4b1d-9747-47fbc50c2fee)

## Join String
Custom node that can take a string value and add pre & post text in one go to produce a full joined string. I created this to allow me to dynamically cycle through many LoRA and create different images.
![JoinString node](https://github.com/user-attachments/assets/df486621-a12b-4bd9-82f9-cb7cdffac4aa)

## Dithering Node
Taking some of the Dithering Algorithms and made a node that allows you generate the cool effects with bunch of options to tweak.
![dithering node](https://github.com/user-attachments/assets/8f68f4f2-092b-4b4f-80fa-7b60d79bf648)

## Image Batch Loader

A custom node for ComfyUI that enables sequential loading of images from a directory with advanced sorting and control options. The node maintains its state between executions, allowing for automatic incremental loading of images in a controlled manner.

### Features

- **Sequential Image Loading**: Automatically increment through images in a directory
- **Multiple File Type Support**: Filter images by extension (PNG, JPG, JPEG, or ALL)
- **Advanced Sorting Options**:
  - Numerical (natural sort for numbered filenames)
  - Alphabetical
  - Creation time
  - Modification time
- **GPU/CUDA Support**: Automatic GPU acceleration when available
- **Directory Reload Control**: Option to force directory rescanning
- **Index Control**: Reset capability and automatic wraparound
- **State Management**: Maintains state between executions for true sequential processing

### Node Inputs

| Input | Type | Description |
|-------|------|-------------|
| directory_path | STRING | Path to the directory containing images |
| file_extension | ["PNG", "JPG", "JPEG", "ALL"] | Filter for specific file types |
| reset_index | BOOLEAN | When True, resets the counter to 0 |
| sort_method | ["alphabetical", "numerical", "creation_time", "modification_time"] | Method to sort the images |
| reload_directory | BOOLEAN | When True, forces directory rescan and index reset |

### Node Outputs

| Output | Type | Description |
|--------|------|-------------|
| image | TENSOR | The loaded image as a GPU tensor |
| current_index | INT | Current position in the sequence |
| total_images | INT | Total number of images in directory |
| filename | STRING | Name of the current image file |

### Sorting Behavior

#### Numerical Sort (Default)
- Handles numbered filenames intelligently
- Example: `["img1.png", "img2.png", "img10.png"]`
- Instead of: `["img1.png", "img10.png", "img2.png"]`

#### Alphabetical Sort
- Standard alphabetical ordering
- Case-insensitive

#### Time-based Sorting
- Creation time: Orders by file creation timestamp
- Modification time: Orders by last modified timestamp


## LLM Prompt To Text File
### Overview
The LLM Prompt To Text File Node is able to take input of text prompts and write them into a single file where each prompt is one line in the output file. It trims and removes undesired characters. Combine this with the Image Batch Loader you can process images from a folder feed them to LLM for prompt generation and write it out to an input file.
I created this node because I needed lots of prompts that I feed into Flux or other models to test LoRA perfromance. So this allows me to create a batched file that has many prompts created from my sample images. 

### Features
- Creates new text files or appends to existing ones
- Cleans input text by:
  - Removing line breaks and carriage returns
  - Stripping special characters while preserving:
    - Commas (,)
    - Periods (.)
    - Double quotes (")
    - Hyphens (-)
  - Normalizing whitespace
- Optional prefix text for each entry
- Detailed operation logging
- Automatic creation of output directories

### Node Inputs
#### Required:
- **text**: The main text content to write (supports multiline input)
- **output_path**: Directory where the file should be written (defaults to ComfyUI output directory if empty)

#### Optional:
- **filename**: Name of the output file (defaults to "output.txt")
- **prefix_text**: Text to prepend to the main content (single line)

### Node Outputs
- **log_output**: A string containing detailed information about the operation, including:
  - Input parameters
  - Text cleaning results
  - File operations performed
  - Any errors encountered

#### With Prefix
```python
# Will add a prefix to the text before writing
node_input = {
    "text": "This is the main content",
    "prefix_text": "Entry:",
    "filename": "log.txt"
}
# Results in: "Entry: This is the main content"
```

### Text Cleaning Behavior
The node automatically cleans input text by:
1. Converting line breaks to spaces
2. Removing special characters except:
   - Letters and numbers
   - Spaces
   - Commas (,)
   - Periods (.)
   - Double quotes (")
   - Hyphens (-)
   - Semi-colon (;)
3. Normalizing multiple spaces to single spaces
4. Trimming leading/trailing whitespace

Example:
```
Input:  "This is a *test* with\nmultiple\nlines and $ special @ characters"
Output: "This is a test with multiple lines and special characters"
```

### File Operation Behavior
- If the file doesn't exist, it creates a new file with the content
- If the file exists, it adds the new content on a new line
- Creates output directories automatically if they don't exist
- Uses UTF-8 encoding for file operations

### Error Handling
- Provides detailed error messages in the log output
- Gracefully handles file access and permission issues
- Reports file existence conflicts and operation results

## Prompt Writer

Another node that take several inputs and designed to generate prompt files alongside images for LoRA Training. Combine this with the Image Batch Loader and other custom nodes like Florence2 and you have the perfect workflow to generate prompts, you can also put the trigger word as the Prefix which is added to each file.

### Features

- Write text content to files specified in the output directory
- Automatically names output files based on associated image filenames with TXT.
- Support for adding prefix Trigger Word text to all written files
- Configurable subdirectory organization, in case you want to run two different LLMs to generate prompts
- Ability to overwite the files if they exist
- Detailed logging of all operations

### Node Parameters

#### Required Parameters

- `text` (STRING): The main text content to write to the file
- `image_filename` (STRING): Name of the associated image file (used to generate the text filename)
- `output_path` (STRING): Custom output directory path (defaults to ComfyUI's output directory if empty)
- `overwrite` (BOOLEAN): Whether to overwrite existing files (defaults to False)

#### Optional Parameters

- `prefix_text` (STRING): Text to add before the main content
- `subdirectory` (STRING): Subdirectory within the output path for file organization

### Output

- `log_output` (STRING): Detailed log of the operation, including:
  - Input parameters used
  - Generated filename
  - Output path details
  - Operation status
  - Any errors encountered

### Error Handling

- Creates output directories if they don't exist
- Prevents accidental file overwrites unless explicitly enabled
- Provides detailed logging of any errors or issues
- Uses UTF-8 encoding for broad character support

## Advanced Text File Reader

Advanced Text File Reader custom node for ComfyUI that enables sequential or random reading of text files, with flexible traversal options and line control. Perfect for batch processing where text needs to be read from external file and feed into txt2img models

### Features

- Multiple text traversal modes:
  - Forward: Read lines sequentially from start to end
  - Reverse: Read lines from end to start
  - Random: Read lines in random order without repetition
- Line skipping capability
- Progress tracking with line counting
- File reloading control
- Counter reset functionality
- Custom starting index support
- UTF-8 encoding support

### Node Parameters

#### Required Parameters

- `file_path` (STRING): Path to the text file to read
- `traversal_mode` (["forward", "reverse", "random"]): How to traverse the file
- `skip_lines` (INT): Number of additional lines to skip (0-10)
- `reset_counter` (BOOLEAN): Whether to reset the line counter
- `reload_file` (BOOLEAN): Force reload the file contents

#### Optional Parameters

- `starting_index` (INT): Custom starting position in the file

### Outputs

1. `current_line` (STRING): The current text line being read
2. `current_line_number` (INT): Current line number (1-based)
3. `total_lines` (INT): Total number of lines in the file
4. `remaining_lines` (INT): Number of lines left to process

### Features in Detail

#### Traversal Modes

- **Forward Mode**: 
  - Reads lines sequentially from beginning to end
  - Wraps around to the start when reaching the end
  
- **Reverse Mode**:
  - Reads lines from end to beginning
  - Wraps around to the end when reaching the start
  
- **Random Mode**:
  - Reads lines in random order
  - Ensures no line is repeated until all lines are read
  - Automatically resets when all lines have been read

#### File Handling

- Automatic file reloading when:
  - A new file path is provided
  - The reload_file flag is set to True
- Maintains state between calls unless reset
- Handles empty files and file not found errors gracefully

#### Line Control

- Skip multiple lines at once
- Reset line counter while maintaining file contents
- Start reading from any position in the file
- Track progress with line counting and remaining lines

### Error Handling

- File not found handling
- Empty file detection
- UTF-8 encoding support
- Proper index boundary handling

## Game Boy Camera Node for ComfyUI

This custom node for ComfyUI applies a Game Boy Camera-style effect to images, including dithering and the iconic 4-color palette. It simulates the aesthetic of Nintendo's Game Boy Camera peripheral from 1998.

### Features

- True Game Boy Camera resolution options (1x, 2x, 4x)
- Original Game Boy color palettes:
  - Greyscale (4 shades)
  - Classic Game Boy green
- Ordered dithering using authentic 8x8 Bayer matrix
- Aspect ratio preservation
- Configurable pixel upscaling

### Node Inputs

- `image`: Input image to process
- `mode`: Color palette selection
  - `greyscale`: Classic 4-shade greyscale
  - `gameboy_green`: Original Game Boy green tones
- `resolution`: Base resolution for processing
  - `1x_gameboy`: 128x112 (original)
  - `2x_gameboy`: 256x224
  - `4x_gameboy`: 512x448
- `upscale_factor`: Final pixel scaling (1-10)

### Notes

- Images are automatically scaled to fit within the chosen Game Boy resolution while maintaining their original aspect ratio
- The upscale factor is applied after processing to create that chunky pixel look
- Best results are typically achieved with the 1x resolution and an upscale factor of 5

## Nested Loop Counter Node for ComfyUI
A custom node that implements a nested loop counter similar to a nested for-loop structure. The node maintains state between executions, allowing for sequential counting through two nested loops.

###Parameters

- max_value: Maximum value for both i and j counters (min: 1, max: 10000)
- increment: Value to increment counters by (min: 1, max: 1000)
- reset: Boolean to force reset both counters to 0

### Outputs

- i: Current value of outer loop counter (integer)
- j: Current value of inner loop counter (integer)
- i_float: Current value of outer loop counter (float)
- j_float: Current value of inner loop counter (float)
- debug_log: String output showing counter states and transitions

### Behavior
The node increments j first. When j reaches max_value, it resets to 0 and increments i. When i reaches max_value, both counters reset to 0. State is maintained between executions unless reset is triggered.

## Image Dimension Calculator

A utility node that calculates upscaled image dimensions based on a scale factor while ensuring the output dimensions are multiples of a specified factor (16, 32, or 64). This is essential for compatibility with AI models that require specific dimension constraints.

### Features

- Accepts single image input and calculates scaled dimensions
- Preserves original aspect ratio during scaling
- Configurable multiple factor (16, 32, or 64)
- Smart rounding algorithm that minimizes aspect ratio drift
- Outputs integer width and height values only (no actual image upscaling)
- Detailed console logging for debugging

### Node Inputs

- `image`: Single image input (batch size must be 1)
- `scale_factor`: Decimal multiplier for dimensions (0.1 to 10.0, step 0.1, default 1.5)
- `multiple_of`: Dimension constraint factor - choose from 16, 32, or 64 (default 64)

### Node Outputs

- `width` (INT): Calculated width rounded to nearest multiple
- `height` (INT): Calculated height rounded to nearest multiple

### How It Works

1. Takes the input image dimensions and multiplies by the scale factor
2. Rounds the width to the nearest multiple of the selected factor
3. Calculates height based on the original aspect ratio
4. Rounds height to the nearest multiple
5. Validates that aspect ratio drift is less than 5% - if not, recalculates starting with height
6. Ensures minimum dimensions match the selected multiple factor

### Example Usage

**Example 1:**
- Input: 512×512 image, scale_factor: 1.5, multiple_of: 64
- Calculation: 768×768
- Output: 768×768 (aspect ratio: 1.0 preserved)

**Example 2:**
- Input: 720×480 image, scale_factor: 2.0, multiple_of: 64
- Calculation: 1440×960
- Output: 1440×960 (aspect ratio: 1.5 preserved)

**Example 3:**
- Input: 720×480 image, scale_factor: 1.5, multiple_of: 32
- Calculation: 1080×720
- Output: 1088×704 (aspect ratio: ~1.545 vs original 1.5, within acceptable range)

### Use Cases

- Preparing dimensions for video generation models
- Calculating target sizes for upscaling workflows
- Ensuring compatibility with AI models that require specific dimension constraints
- Planning image processing pipelines with predictable output dimensions

## Image Dimension Size

A simple utility node that analyzes image dimensions and returns either the longest or shortest edge value, plus an upscaled value multiplied by a user-defined multiplier. Useful for determining image orientation and making conditional decisions based on image dimensions.

### Features

- Detects longest or shortest edge from image dimensions
- Simple dropdown selection for edge type
- Multiplier input (1–10) to produce an upscaled dimension value
- Returns integer values for easy integration with other nodes
- Console logging for debugging

### Node Inputs

- `image`: Input image to analyze
- `edge`: Edge selection - choose from:
  - `long`: Uses the longer dimension (width or height)
  - `short`: Uses the shorter dimension (width or height)
- `multiplier` (INT, 1–10, default 1): Factor to multiply the selected edge by

### Node Outputs

- `edge_value` (INT): The detected edge dimension as an integer
- `upscaled_value` (INT): The edge dimension multiplied by the multiplier

### How It Works

1. Analyzes the input image dimensions (width and height)
2. Compares the two values
3. Selects the maximum value if "long" is selected, minimum if "short"
4. Multiplies the selected value by the multiplier to produce the upscaled value

### Example Usage

**Example 1: Portrait Image**
- Input: 512×768 image, edge: "long", multiplier: 2
- Output: edge_value: 768, upscaled_value: 1536

**Example 2: Landscape Image**
- Input: 1920×1080 image, edge: "short", multiplier: 1
- Output: edge_value: 1080, upscaled_value: 1080

**Example 3: Square Image**
- Input: 512×512 image, edge: "long", multiplier: 4
- Output: edge_value: 512, upscaled_value: 2048

### Use Cases

- Determining image orientation (portrait vs landscape)
- Conditional scaling based on longest or shortest edge
- Generating target dimensions for upscalers
- Setting dynamic constraints for image processing
- Creating adaptive workflows that respond to image dimensions
- Feeding dimension values to other nodes for calculations