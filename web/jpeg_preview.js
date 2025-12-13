import { app } from "../../scripts/app.js";

// Register extension for WWAA_JPEGPreview
app.registerExtension({
    name: "WWAA.JPEGPreview",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "WWAA_JPEGPreview") {
            const onExecuted = nodeType.prototype.onExecuted;

            nodeType.prototype.onExecuted = function (message) {
                onExecuted?.apply(this, arguments);

                // Display image info below the image preview
                if (message.image_info && message.image_info.length > 0) {
                    const info = message.image_info[0];
                    const infoText = `${info.width}x${info.height} | ${info.size_kb} KB | Quality: ${info.quality}`;
                    
                    // Find or create info widget
                    let infoWidget = this.widgets?.find(w => w.name === "jpeg_info");
                    
                    if (!infoWidget) {
                        // Create a custom widget to display the info
                        infoWidget = this.addCustomWidget({
                            name: "jpeg_info",
                            type: "text",
                            value: infoText,
                            options: {},
                            computeSize: function(width) {
                                return [width, 30];
                            },
                            draw: function(ctx, node, width, y) {
                                ctx.save();
                                ctx.fillStyle = "#AAA";
                                ctx.font = "14px monospace";
                                ctx.textAlign = "center";
                                ctx.fillText(this.value, width / 2, y + 20);
                                ctx.restore();
                            }
                        });
                    } else {
                        infoWidget.value = infoText;
                    }
                    
                    // Force node to redraw
                    this.setDirtyCanvas(true, true);
                }
            };
        }
    }
});
