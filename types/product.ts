export interface Product {
  id: string;
  name: string;
  price: number;
  in_stock: boolean;
  why_for_you?: string;
  discounted_price?: number;
  image_url?: string;
  rating?: number;
  colors?: string[];
  sizes?: string[];
  occasion_tags?: string[];
}
