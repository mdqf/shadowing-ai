import React from "react";
import { Box, Typography, Paper } from "@mui/material";

export const ProgressPage: React.FC = () => (
  <Box sx={{ maxWidth: 800, mx: "auto", mt: 4 }}>
    <Paper sx={{ p: 4, borderRadius: "var(--md-sys-shape-corner-large)", backgroundColor: "var(--md-sys-color-surface-container-low)" }}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>نمودار پیشرفت و تاریخچه</Typography>
      <Typography variant="body2" sx={{ color: "var(--md-sys-color-on-surface-variant)", mt: 1 }}>
        روند بهبود دقت تلفظ، اتصال کلمات و فونم‌ها در اینجا گزارش می‌شود.
      </Typography>
    </Paper>
  </Box>
);