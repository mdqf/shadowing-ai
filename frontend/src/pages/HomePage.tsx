import React from "react";
import { Box, Typography, Button, Paper } from "@mui/material";
import { useNavigate } from "react-router-dom";
import RecordVoiceOverRoundedIcon from "@mui/icons-material/RecordVoiceOverRounded";

export const HomePage: React.FC = () => {
  const navigate = useNavigate();
  return (
    <Box sx={{ maxWidth: 800, mx: "auto", mt: 4 }}>
      <Paper
        elevation={0}
        sx={{
          p: 4,
          borderRadius: "var(--md-sys-shape-corner-extra-large)",
          backgroundColor: "var(--md-sys-color-surface-container-low)",
          border: "1px solid var(--md-sys-color-outline-variant)",
        }}
      >
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1, color: "var(--md-sys-color-on-surface)" }}>
          به Shadowing AI خوش آمدید 👋
        </Typography>
        <Typography variant="body1" sx={{ color: "var(--md-sys-color-on-surface-variant)", mb: 3 }}>
          تمرین هوشمند تلفظ، ریتم و اتصال کلمات با فیلم و سریال‌های دلخواه شما با استفاده از هوش مصنوعی.
        </Typography>
        <Button
          variant="contained"
          startIcon={<RecordVoiceOverRoundedIcon />}
          onClick={() => navigate("/practice/default")}
          sx={{
            borderRadius: "var(--md-sys-shape-corner-full)",
            backgroundColor: "var(--md-sys-color-primary)",
            color: "var(--md-sys-color-on-primary)",
            px: 3,
            py: 1.2,
            textTransform: "none",
            "&:hover": { backgroundColor: "var(--md-sys-color-primary-container)" },
          }}
        >
          شروع تمرین جدید
        </Button>
      </Paper>
    </Box>
  );
};