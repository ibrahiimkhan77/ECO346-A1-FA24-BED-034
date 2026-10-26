library(tidyverse)

PROV <- 3  # Sindh
AREA <- 1  # rural

weighted_mean <- function(x, w) {
  sum(w * x) / sum(w)
}

# Smallest x where cumulative weight share >= p (the assignment's definition)
weighted_quantile <- function(x, w, p) {
  ord <- order(x)
  x_sorted <- x[ord]
  w_sorted <- w[ord]
  cum_share <- cumsum(w_sorted) / sum(w_sorted)
  x_sorted[which(cum_share >= p)[1]]
}

person <- read_csv("data/pslm_person_subset.csv", show_col_types = FALSE)
hh <- read_csv("data/pslm_hh_subset.csv", show_col_types = FALSE)

cat("Duplicated hhid in household file:", sum(duplicated(hh$hhid)), "\n")

hh_keys <- hh %>% select(hhid, hhweight, prov_code, urban_rural)
person_all <- person %>% left_join(hh_keys, by = "hhid")

cat("Person rows before join:", nrow(person), "\n")
cat("Person rows after join: ", nrow(person_all), "\n")
cat("Missing hhweight after join:", sum(is.na(person_all$hhweight)), "\n")

person_v <- person_all %>% filter(prov_code == PROV, urban_rural == AREA)

lit_sample <- person_v %>%
  filter(age >= 10, age <= 64, !is.na(literate)) %>%
  mutate(
    band_start = 10 + 5 * ((age - 10) %/% 5),
    band = paste0(band_start, "-", band_start + 4),
    band_mid = band_start + 2,
    sex_label = if_else(sex == 1, "Men", "Women")
  )

students <- person_v %>% filter(!is.na(ed_total), ed_total > 0)

cat("Persons in variant:", nrow(person_v), "\n")
cat("Literacy sample:", nrow(lit_sample), "\n")
cat("Students:", nrow(students), "\n")