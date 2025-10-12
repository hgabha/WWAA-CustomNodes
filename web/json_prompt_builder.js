import { app } from "../../scripts/app.js";

// Register extension for WWAA_JSONPromptBuilder
app.registerExtension({
    name: "WWAA.JSONPromptBuilder",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "WWAA_JSONPromptBuilder") {

            // Store the original onNodeCreated
            const onNodeCreated = nodeType.prototype.onNodeCreated;

            nodeType.prototype.onNodeCreated = function() {
                const result = onNodeCreated?.apply(this, arguments);

                // Get the subject_category widget
                const subjectCategoryWidget = this.widgets.find(w => w.name === "subject_category");

                if (!subjectCategoryWidget) return result;

                // Store original widget properties on first run
                if (!this.widgetOriginalProps) {
                    this.widgetOriginalProps = {};
                    this.widgets.forEach(widget => {
                        this.widgetOriginalProps[widget.name] = {
                            type: widget.type,
                            computeSize: widget.computeSize
                        };
                    });
                }

                // Function to update widget visibility based on category
                const updateWidgetVisibility = () => {
                    const category = subjectCategoryWidget.value;

                    // Define which widgets are visible for each category
                    const humanOnlyWidgets = [
                        "gender_presentation",
                        "age_bracket",
                        "hair_length",
                        "hair_style",
                        "hair_color"
                    ];

                    const humanAnimalWidgets = [
                        "facial_expression",
                        "makeup_details",
                        "face_accessories",
                        "body_pose",
                        "clothing",
                        "body_features"
                    ];

                    // Update visibility for each widget
                    this.widgets.forEach(widget => {
                        const origProps = this.widgetOriginalProps[widget.name];
                        if (!origProps) return;

                        let shouldShow = true;

                        // Human-only fields
                        if (humanOnlyWidgets.includes(widget.name)) {
                            shouldShow = category === "human";
                        }

                        // Human/Animal fields
                        if (humanAnimalWidgets.includes(widget.name)) {
                            shouldShow = ["human", "animal"].includes(category);
                        }

                        // Apply visibility
                        if (shouldShow) {
                            widget.type = origProps.type;
                            widget.computeSize = origProps.computeSize;
                        } else {
                            widget.type = "converted-widget";
                            widget.computeSize = () => [0, -4];
                        }
                    });

                    // Force node to recalculate its size
                    this.setSize(this.computeSize());
                    this.setDirtyCanvas(true, true);
                };

                // Override the callback for subject_category
                const originalCallback = subjectCategoryWidget.callback;
                subjectCategoryWidget.callback = function() {
                    if (originalCallback) {
                        originalCallback.apply(this, arguments);
                    }
                    updateWidgetVisibility();
                };

                // Run once on creation to set initial state
                updateWidgetVisibility();

                return result;
            };
        }
    }
});
