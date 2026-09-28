import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Paper,
  Typography,
  Button,
  Chip,
  Card,
  CardMedia,
  CardContent,
  CardActions,
  TextField,
  InputAdornment,
  LinearProgress,
} from "@mui/material";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import PlayArrowRoundedIcon from "@mui/icons-material/PlayArrowRounded";
import SubtitlesRoundedIcon from "@mui/icons-material/SubtitlesRounded";
import AccessTimeRoundedIcon from "@mui/icons-material/AccessTimeRounded";
import { COURSES_DATA } from "../data/coursesData";

export interface VideoCourse {
  id: string;
  title: string;
  description: string;
  level: "A1" | "A2" | "B1" | "B2" | "C1";
  duration: string;
  sentenceCount: number;
  progressPercentage: number;
  thumbnailUrl: string;
  videoUrl?: string;
  srtUrl?: string;
}

const SAMPLE_COURSES: VideoCourse[] = Object.values(COURSES_DATA);

interface LibraryPageProps {
  onSelectCourse?: (course: VideoCourse) => void;
}

export const LibraryPage: React.FC<LibraryPageProps> = ({ onSelectCourse }) => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedLevel, setSelectedLevel] = useState<string>("All");

  const levels = ["All", "A1", "A2", "B1", "B2", "C1"];

  const filteredCourses = SAMPLE_COURSES.filter((course) => {
    const matchesSearch =
      course.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      course.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesLevel = selectedLevel === "All" || course.level === selectedLevel;
    return matchesSearch && matchesLevel;
  });

  return (
    <Box sx={{ maxWidth: 1100, mx: "auto", display: "flex", flexDirection: "column", gap: 3 }}>
      {/* Header Banner */}
      <Paper
        elevation={0}
        sx={{
          p: 4,
          borderRadius: "var(--md-sys-shape-corner-extra-large)",
          backgroundColor: "var(--md-sys-color-surface-container-low)",
          border: "1px solid var(--md-sys-color-outline-variant)",
          display: "flex",
          flexDirection: "column",
          gap: 1.5,
        }}
      >
        <Typography variant="h4" sx={{ fontWeight: 800, color: "var(--md-sys-color-on-surface)" }}>
          کتابخانه ویدیوها و دروس Shadowing
        </Typography>
        <Typography variant="body1" sx={{ color: "var(--md-sys-color-on-surface-variant)" }}>
          ویدیو یا درس مورد نظر خود را انتخاب کرده و تمرین تلفظ صوتی و تحلیل آوایی V2 را آغاز کنید.
        </Typography>
      </Paper>

      {/* Filter & Search Toolbar */}
      <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", alignItems: "center", justifyContent: "space-between" }}>
        <TextField
          size="small"
          placeholder="جستجوی عنوان یا توضیحات درس..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchRoundedIcon />
                </InputAdornment>
              ),
              sx: { borderRadius: "var(--md-sys-shape-corner-full)", minWidth: 280 },
            },
          }}
        />

        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          {levels.map((lvl) => (
            <Chip
              key={lvl}
              label={lvl === "All" ? "همه سطوح" : `سطح ${lvl}`}
              clickable
              onClick={() => setSelectedLevel(lvl)}
              sx={{
                borderRadius: "var(--md-sys-shape-corner-full)",
                backgroundColor:
                  selectedLevel === lvl
                    ? "var(--md-sys-color-primary-container)"
                    : "var(--md-sys-color-surface-container)",
                color:
                  selectedLevel === lvl
                    ? "var(--md-sys-color-on-primary-container)"
                    : "var(--md-sys-color-on-surface-variant)",
                fontWeight: selectedLevel === lvl ? 700 : 500,
              }}
            />
          ))}
        </Box>
      </Box>

      {/* Course Cards Grid using CSS Grid */}
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)" }, gap: 3 }}>
        {filteredCourses.map((course) => (
          <Card
            key={course.id}
            elevation={0}
            sx={{
              borderRadius: "var(--md-sys-shape-corner-extra-large)",
              backgroundColor: "var(--md-sys-color-surface-container-low)",
              border: "1px solid var(--md-sys-color-outline-variant)",
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
              transition: "transform 0.2s, box-shadow 0.2s",
              "&:hover": {
                transform: "translateY(-4px)",
                boxShadow: "0 8px 24px rgba(0,0,0,0.08)",
              },
            }}
          >
            <Box sx={{ position: "relative" }}>
              <CardMedia component="img" height="160" image={course.thumbnailUrl} alt={course.title} />
              <Chip
                label={course.level}
                size="small"
                sx={{
                  position: "absolute",
                  top: 12,
                  right: 12,
                  backgroundColor: "var(--md-sys-color-primary)",
                  color: "var(--md-sys-color-on-primary)",
                  fontWeight: 700,
                }}
              />
            </Box>

            <CardContent sx={{ p: 2.5, flexGrow: 1, display: "flex", flexDirection: "column", gap: 1 }}>
              <Typography variant="h6" sx={{ fontWeight: 700, fontSize: "17px" }}>
                {course.title}
              </Typography>
              <Typography variant="body2" sx={{ color: "var(--md-sys-color-on-surface-variant)", lineHeight: 1.6 }}>
                {course.description}
              </Typography>

              <Box sx={{ display: "flex", gap: 2, mt: 1, color: "var(--md-sys-color-on-surface-variant)" }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                  <AccessTimeRoundedIcon sx={{ fontSize: 16 }} />
                  <Typography variant="caption">{course.duration}</Typography>
                </Box>
                <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                  <SubtitlesRoundedIcon sx={{ fontSize: 16 }} />
                  <Typography variant="caption">{course.sentenceCount} جمله</Typography>
                </Box>
              </Box>

              {course.progressPercentage > 0 && (
                <Box sx={{ mt: 1.5 }}>
                  <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                    <Typography variant="caption">پیشرفت تمرین</Typography>
                    <Typography variant="caption" sx={{ fontWeight: 700 }}>{course.progressPercentage}%</Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={course.progressPercentage}
                    sx={{ borderRadius: 4, height: 6, backgroundColor: "var(--md-sys-color-surface-container)" }}
                  />
                </Box>
              )}
            </CardContent>

            <CardActions sx={{ p: 2, pt: 0 }}>
              <Button
                fullWidth
                variant="contained"
                startIcon={<PlayArrowRoundedIcon />}
                onClick={() => {
                  onSelectCourse?.(course);
                  navigate(`/practice/${course.id}`); // <-- هدایت به صفحه تمرین با آی‌دی درس
                }}
                sx={{
                  borderRadius: "var(--md-sys-shape-corner-full)",
                  backgroundColor: "var(--md-sys-color-primary)",
                  color: "var(--md-sys-color-on-primary)",
                  fontWeight: 700,
                  textTransform: "none",
                }}
              >
                شروع تمرین این درس
              </Button>
            </CardActions>
          </Card>
        ))}
      </Box>
    </Box>
  );
};

export default LibraryPage;