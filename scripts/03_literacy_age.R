source("scripts/00_prepare.R")
dir.create("figures", showWarnings = FALSE)

# ---- band table: one row per sex and band ----
band_table <- lit_sample %>%
  group_by(sex_label, band, band_mid) %>%
  summarise(
    n = n(),
    rate = 100 * weighted_mean(literate, hhweight),
    .groups = "drop"
  ) %>%
  mutate(thin = n < 30)

write_csv(band_table, "figures/band_table_R.csv")

# ---- wide version for the README table and the gap calculation ----
wide <- band_table %>%
  select(band, band_mid, sex_label, n, rate) %>%
  pivot_wider(names_from = sex_label, values_from = c(n, rate)) %>%
  arrange(band_mid)

md_lines <- c(
  "| Band | Women n | Women literacy % | Men n | Men literacy % |",
  "|---|---|---|---|---|",
  sprintf("| %s | %s | %.1f | %s | %.1f |",
          wide$band, wide$n_Women, wide$rate_Women, wide$n_Men, wide$rate_Men)
)

# ---- band with the largest gap between men and women ----
gap_df <- wide %>% mutate(gap = rate_Men - rate_Women)
top <- gap_df %>% slice_max(abs(gap), n = 1)

# ---- figure ----
colours <- c(Men = "#1b6ca8", Women = "#c0392b")
end_points <- band_table %>% filter(band_mid == max(band_mid))
solid_points <- band_table %>% filter(!thin)
hollow_points <- band_table %>% filter(thin)

p <- ggplot(band_table, aes(band_mid, rate, colour = sex_label)) +
  geom_line(aes(group = sex_label), linewidth = 0.8) +
  geom_point(data = solid_points, size = 3) +
  geom_point(data = hollow_points, shape = 21, fill = "white",
             size = 3, stroke = 1.2) +
  geom_text(data = end_points, aes(label = sex_label),
            hjust = 0, nudge_x = 1, fontface = "bold") +
  annotate("segment", x = top$band_mid, xend = top$band_mid,
           y = top$rate_Women, yend = top$rate_Men,
           colour = "grey30", linewidth = 0.6) +
  annotate("text", x = top$band_mid, y = (top$rate_Women + top$rate_Men) / 2,
           label = paste0("Largest gap: ", round(abs(top$gap), 1),
                          " points\n(ages ", top$band, ")"),
           hjust = -0.1, colour = "grey20", size = 3.5) +
  scale_colour_manual(values = colours) +
  scale_x_continuous(breaks = seq(12, 62, 5), limits = c(10, 70)) +
  scale_y_continuous(limits = c(0, 100)) +
  labs(
    title = paste0("Rural Sindh: the literacy gap between men and women is widest at ages ",
                   top$band, " (", round(abs(top$gap), 1), " points)"),
    x = "Age (band midpoint)",
    y = "Literacy rate (%)",
    caption = stringr::str_wrap(
      paste0("Source: PSLM 2019-20 person file. Sample: persons aged 10-64 in Sindh rural, ",
             "literate not missing (n = ", nrow(lit_sample), "). Weighted by hhweight. ",
             "Hollow markers: fewer than 30 observations in that band and sex."),
      width = 110)
  ) +
  theme_minimal(base_size = 11) +
  theme(legend.position = "none",
        plot.title = element_text(face = "bold", size = 11),
        plot.title.position = "plot", plot.caption.position = "plot",
        panel.grid.minor = element_blank())

ggsave("figures/literacy_age.svg", p, width = 9, height = 5.5)

# ---- numbers for the README and the Google Form ----
get_rate <- function(b, s) {
  round(band_table$rate[band_table$band == b & band_table$sex_label == s], 1)
}
cat("15-19: Women", get_rate("15-19", "Women"), " Men", get_rate("15-19", "Men"), "\n")
cat("55-59: Women", get_rate("55-59", "Women"), " Men", get_rate("55-59", "Men"), "\n")
cat("Largest gap band:", top$band, " gap:", round(abs(top$gap), 1), "\n")
cat("\nREADME table:\n")
cat(md_lines, sep = "\n")
cat("\n")
print(as.data.frame(band_table))
#.