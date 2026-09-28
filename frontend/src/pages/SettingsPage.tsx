import React from "react";
import { Box, Typography, Paper } from "@mui/material";

export const SettingsPage: React.FC = () => (
  <Box sx={{ maxWidth: 800, mx: "auto", mt: 4 }}>
    <Paper sx={{ p: 4, borderRadius: "var(--md-sys-shape-corner-large)", backgroundColor: "var(--md-sys-color-surface-container-low)" }}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>تنظیمات سیستم</Typography>
      <Typography variant="body2" sx={{ color: "var(--md-sys-color-on-surface-variant)", mt: 1 }}>
        تنظیمات مربوط به میکروفون، کلیدهای API و پارامترهای تحلیل صوتی.
      </Typography>
    </Paper>
  </Box>
);