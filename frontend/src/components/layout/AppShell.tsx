import React from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  Box,
  IconButton,
  Typography,
  Tooltip,
  useMediaQuery,
  useTheme as useMuiTheme,
  Chip
} from "@mui/material";
import HomeRoundedIcon from "@mui/icons-material/HomeRounded";
import VideoLibraryRoundedIcon from "@mui/icons-material/VideoLibraryRounded";
import RecordVoiceOverRoundedIcon from "@mui/icons-material/RecordVoiceOverRounded";
import InsightsRoundedIcon from "@mui/icons-material/InsightsRounded";
import SettingsRoundedIcon from "@mui/icons-material/SettingsRounded";
import DarkModeRoundedIcon from "@mui/icons-material/DarkModeRounded";
import LightModeRoundedIcon from "@mui/icons-material/LightModeRounded";
import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import { useTheme } from "../../context/ThemeContext";

const navItems = [
  { label: "خانه", path: "/", icon: <HomeRoundedIcon /> },
  { label: "کتابخانه", path: "/library", icon: <VideoLibraryRoundedIcon /> },
  { label: "تمرین", path: "/practice/default", icon: <RecordVoiceOverRoundedIcon /> },
  { label: "پیشرفت", path: "/progress", icon: <InsightsRoundedIcon /> },
  { label: "تنظیمات", path: "/settings", icon: <SettingsRoundedIcon /> },
];

export const AppShell: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { mode, toggleTheme } = useTheme();
  const muiTheme = useMuiTheme();
  const isMobile = useMediaQuery(muiTheme.breakpoints.down("md"));

  const isSelected = (path: string) => {
    if (path === "/") return location.pathname === "/";
    return location.pathname.startsWith(path.split("/")[1] ? `/${path.split("/")[1]}` : path);
  };

  return (
    <Box sx={{ display: "flex", flexDirection: isMobile ? "column" : "row", minHeight: "100vh" }}>
      {/* --- Top App Bar --- */}
      <Box
        component="header"
        sx={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          height: 64,
          backgroundColor: "var(--md-sys-color-surface-container-low)",
          color: "var(--md-sys-color-on-surface)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: 3,
          zIndex: 1100,
          borderBottom: "1px solid var(--md-sys-color-outline-variant)",
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <Typography
            variant="h6"
            sx={{
              fontWeight: 700,
              letterSpacing: 0.5,
              background: "linear-gradient(135deg, var(--md-sys-color-primary) 0%, var(--md-sys-color-tertiary) 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            Shadowing AI
          </Typography>
          <Chip
            icon={<CheckCircleRoundedIcon sx={{ fontSize: "16px !important", color: "var(--md-custom-match) !important" }} />}
            label="Backend Ready"
            size="small"
            sx={{
              backgroundColor: "var(--md-sys-color-surface-container-high)",
              color: "var(--md-sys-color-on-surface-variant)",
              fontSize: "12px",
              height: "26px",
            }}
          />
        </Box>

        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Tooltip title={mode === "dark" ? "حالت روشن" : "حالت تاریک"}>
            <IconButton
              onClick={toggleTheme}
              sx={{
                color: "var(--md-sys-color-on-surface-variant)",
                backgroundColor: "var(--md-sys-color-surface-container)",
                "&:hover": { backgroundColor: "var(--md-sys-color-surface-container-high)" },
              }}
            >
              {mode === "dark" ? <LightModeRoundedIcon /> : <DarkModeRoundedIcon />}
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* --- Desktop Navigation Rail --- */}
      {!isMobile && (
        <Box
          component="nav"
          sx={{
            width: 88,
            pt: "80px",
            pb: 2,
            backgroundColor: "var(--md-sys-color-surface-container-low)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 2,
            position: "fixed",
            top: 0,
            bottom: 0,
            left: 0,
            zIndex: 1000,
            borderRight: "1px solid var(--md-sys-color-outline-variant)",
          }}
        >
          {navItems.map((item) => {
            const active = isSelected(item.path);
            return (
              <Box
                key={item.path}
                onClick={() => navigate(item.path)}
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  cursor: "pointer",
                  width: "100%",
                  gap: 0.5,
                }}
              >
                <Box
                  sx={{
                    width: 56,
                    height: 32,
                    borderRadius: "var(--md-sys-shape-corner-full)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    backgroundColor: active ? "var(--md-sys-color-secondary-container)" : "transparent",
                    color: active
                      ? "var(--md-sys-color-on-secondary-container)"
                      : "var(--md-sys-color-on-surface-variant)",
                    transition: "all var(--md-sys-motion-duration-short) var(--md-sys-motion-easing-standard)",
                    "&:hover": {
                      backgroundColor: active
                        ? "var(--md-sys-color-secondary-container)"
                        : "var(--md-sys-color-surface-container-high)",
                    },
                  }}
                >
                  {item.icon}
                </Box>
                <Typography
                  sx={{
                    fontSize: "12px",
                    fontWeight: active ? 600 : 400,
                    color: active
                      ? "var(--md-sys-color-on-surface)"
                      : "var(--md-sys-color-on-surface-variant)",
                  }}
                >
                  {item.label}
                </Typography>
              </Box>
            );
          })}
        </Box>
      )}

      {/* --- Main Content Stage --- */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          pt: "80px",
          pb: isMobile ? "80px" : 3,
          pl: isMobile ? 2 : "104px",
          pr: 2,
          minHeight: "100vh",
          backgroundColor: "var(--md-sys-color-surface)",
        }}
      >
        <Outlet />
      </Box>

      {/* --- Mobile Bottom Navigation Bar --- */}
      {isMobile && (
        <Box
          component="nav"
          sx={{
            position: "fixed",
            bottom: 0,
            left: 0,
            right: 0,
            height: 64,
            backgroundColor: "var(--md-sys-color-surface-container-low)",
            display: "flex",
            justifyContent: "space-around",
            alignItems: "center",
            borderTop: "1px solid var(--md-sys-color-outline-variant)",
            zIndex: 1100,
          }}
        >
          {navItems.map((item) => {
            const active = isSelected(item.path);
            return (
              <Box
                key={item.path}
                onClick={() => navigate(item.path)}
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 0.25,
                  cursor: "pointer",
                }}
              >
                <Box
                  sx={{
                    width: 48,
                    height: 28,
                    borderRadius: "var(--md-sys-shape-corner-full)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    backgroundColor: active ? "var(--md-sys-color-secondary-container)" : "transparent",
                    color: active
                      ? "var(--md-sys-color-on-secondary-container)"
                      : "var(--md-sys-color-on-surface-variant)",
                  }}
                >
                  {item.icon}
                </Box>
                <Typography
                  sx={{
                    fontSize: "11px",
                    fontWeight: active ? 600 : 400,
                    color: active
                      ? "var(--md-sys-color-on-surface)"
                      : "var(--md-sys-color-on-surface-variant)",
                  }}
                >
                  {item.label}
                </Typography>
              </Box>
            );
          })}
        </Box>
      )}
    </Box>
  );
};