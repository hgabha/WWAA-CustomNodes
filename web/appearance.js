import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "WWAA.appearance", // Extension name
    async nodeCreated(node) {
        // Check if the node's comfyClass starts with "WWAA_"
        if (node.comfyClass.startsWith("WWAA_")) {
            // Apply styling
            node.color = "#4e2d12ff";
            node.bgcolor = "#92511bff";
        }
    }
});
