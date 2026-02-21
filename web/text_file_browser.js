import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "WWAA.TextFileBrowser",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "WWAA_TextFileBrowser") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = function() {
                const result = onNodeCreated?.apply(this, arguments);
                
                // Find the directory path widget
                const directoryWidget = this.widgets?.find(w => w.name === "directory_path");
                
                if (!directoryWidget) {
                    console.error("[WWAA_TextFileBrowser] Could not find directory_path widget");
                    return result;
                }
                
                // Create the file selector dropdown widget
                const fileWidget = this.addWidget(
                    "combo",
                    "selected_file",
                    "No files found",
                    (value) => {
                        console.log(`[WWAA_TextFileBrowser] File selected: ${value}`);
                        // Store the selected file for persistence
                        this.selectedFileValue = value;
                    },
                    {
                        values: ["No files found"]
                    }
                );
                
                // Store last directory to detect changes
                // Initialize to null so first load doesn't skip
                if (this.lastDirectory === undefined) {
                    this.lastDirectory = null;
                }
                if (this.selectedFileValue === undefined) {
                    this.selectedFileValue = null;
                }
                
                // Function to scan directory and update dropdown
                const updateFileList = async () => {
                    const directory = directoryWidget.value;
                    
                    console.log(`[WWAA_TextFileBrowser] updateFileList called with directory: '${directory}'`);
                    console.log(`[WWAA_TextFileBrowser] Last directory: '${this.lastDirectory}'`);
                    console.log(`[WWAA_TextFileBrowser] Selected file value: '${this.selectedFileValue}'`);
                    
                    // Check if directory actually changed
                    const directoryChanged = directory !== this.lastDirectory;
                    
                    if (!directoryChanged && fileWidget.options.values.length > 1 && this.selectedFileValue) {
                        console.log("[WWAA_TextFileBrowser] Directory unchanged, keeping current selection");
                        // Ensure the widget shows the correct value
                        if (fileWidget.value !== this.selectedFileValue) {
                            fileWidget.value = this.selectedFileValue;
                            console.log(`[WWAA_TextFileBrowser] Restored widget value to: ${this.selectedFileValue}`);
                        }
                        return;
                    }
                    
                    if (!directory || directory.trim() === "") {
                        console.log("[WWAA_TextFileBrowser] Directory is empty");
                        fileWidget.options.values = ["No files found"];
                        fileWidget.value = "No files found";
                        this.lastDirectory = directory;
                        this.selectedFileValue = null;
                        return;
                    }
                    
                    try {
                        console.log(`[WWAA_TextFileBrowser] Calling API for directory: ${directory}`);
                        
                        // Call Python backend to get file list
                        const body = {
                            directory_path: directory
                        };
                        
                        const response = await api.fetchApi("/wwaa/get_text_files", {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json",
                            },
                            body: JSON.stringify(body)
                        });
                        
                        const data = await response.json();
                        console.log(`[WWAA_TextFileBrowser] API response:`, data);
                        
                        if (data.files && data.files.length > 0) {
                            fileWidget.options.values = data.files;
                            
                            // If directory didn't change and we have a previous selection, keep it
                            if (!directoryChanged && this.selectedFileValue && data.files.includes(this.selectedFileValue)) {
                                fileWidget.value = this.selectedFileValue;
                                console.log(`[WWAA_TextFileBrowser] Kept previous selection: ${this.selectedFileValue}`);
                            }
                            // If directory changed, try to restore the same file name if it exists
                            else if (directoryChanged && this.selectedFileValue && data.files.includes(this.selectedFileValue)) {
                                fileWidget.value = this.selectedFileValue;
                                console.log(`[WWAA_TextFileBrowser] Restored previous selection in new directory: ${this.selectedFileValue}`);
                            } 
                            // Otherwise use first file
                            else {
                                fileWidget.value = data.files[0];
                                this.selectedFileValue = data.files[0];
                                console.log(`[WWAA_TextFileBrowser] Set to first file: ${data.files[0]}`);
                            }
                            
                            console.log(`[WWAA_TextFileBrowser] Updated dropdown with ${data.files.length} files`);
                        } else {
                            fileWidget.options.values = ["No files found"];
                            fileWidget.value = "No files found";
                            this.selectedFileValue = null;
                            console.log("[WWAA_TextFileBrowser] No files found");
                        }
                        
                        this.lastDirectory = directory;
                    } catch (error) {
                        console.error("[WWAA_TextFileBrowser] Error fetching file list:", error);
                        fileWidget.options.values = ["Error reading directory"];
                        fileWidget.value = "Error reading directory";
                        this.selectedFileValue = null;
                    }
                };
                
                // Override directory widget callback to update file list only on change
                const originalCallback = directoryWidget.callback;
                directoryWidget.callback = function(...args) {
                    console.log("[WWAA_TextFileBrowser] Directory widget callback triggered");
                    if (originalCallback) {
                        originalCallback.apply(this, args);
                    }
                    updateFileList();
                };
                
                // Initial update - check if we're restoring from saved state
                setTimeout(() => {
                    console.log("[WWAA_TextFileBrowser] Initial file list update");
                    console.log(`[WWAA_TextFileBrowser] Pre-update - lastDirectory: '${this.lastDirectory}', selectedFileValue: '${this.selectedFileValue}'`);
                    
                    // If we have a saved directory and selected file, don't update
                    if (this.lastDirectory && this.selectedFileValue) {
                        console.log("[WWAA_TextFileBrowser] Skipping initial update - restoring from saved state");
                        // Just ensure the widget values are populated
                        if (fileWidget.options.values.length === 1 && fileWidget.options.values[0] === "No files found") {
                            updateFileList();
                        }
                    } else {
                        updateFileList();
                    }
                }, 100);
                
                return result;
            };
            
            // Override serialize to save selected file
            const onSerialize = nodeType.prototype.onSerialize;
            nodeType.prototype.onSerialize = function(info) {
                const result = onSerialize?.apply(this, arguments);
                if (this.selectedFileValue) {
                    info.selectedFileValue = this.selectedFileValue;
                }
                if (this.lastDirectory) {
                    info.lastDirectory = this.lastDirectory;
                }
                console.log(`[WWAA_TextFileBrowser] Serializing - lastDirectory: '${this.lastDirectory}', selectedFileValue: '${this.selectedFileValue}'`);
                return result;
            };
            
            // Override configure to restore selected file
            const onConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function(info) {
                const result = onConfigure?.apply(this, arguments);
                if (info.selectedFileValue !== undefined) {
                    this.selectedFileValue = info.selectedFileValue;
                    console.log(`[WWAA_TextFileBrowser] Restored selectedFileValue: ${this.selectedFileValue}`);
                }
                if (info.lastDirectory !== undefined) {
                    this.lastDirectory = info.lastDirectory;
                    console.log(`[WWAA_TextFileBrowser] Restored lastDirectory: ${this.lastDirectory}`);
                }
                return result;
            };
            
            // Override getExtraMenuOptions to add refresh button
            const getExtraMenuOptions = nodeType.prototype.getExtraMenuOptions;
            nodeType.prototype.getExtraMenuOptions = function(_, options) {
                const result = getExtraMenuOptions?.apply(this, arguments);
                
                options.push({
                    content: "Refresh File List",
                    callback: () => {
                        const directoryWidget = this.widgets?.find(w => w.name === "directory_path");
                        if (directoryWidget) {
                            console.log("[WWAA_TextFileBrowser] Manual refresh triggered");
                            this.lastDirectory = null; // Force refresh
                            if (directoryWidget.callback) {
                                directoryWidget.callback();
                            }
                        }
                    }
                });
                
                return result;
            };
        }
    }
});
