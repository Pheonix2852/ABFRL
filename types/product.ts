export interface Product {
  id: string;
  name: string;
  category?: string;
  subcategory?: string;
  gender_tags?: string[];
  price: number;
  in_stock: boolean;
  online_stock?: number;
  why_for_you?: string;
  discounted_price?: number;
  image_url?: string;
  rating?: number;
  colors?: string[];
  sizes?: string[];
  occasion_tags?: string[];
  availability_badge?: string;
}
