export type BudgetRange = {
  min: number;
  max: number;
  label: string;
};

export type OccasionType = "gifting" | "self_wear" | "family";

export interface OnboardingAnswers {
  budget: BudgetRange;
  colors: string[];
  occasion: OccasionType;
}
