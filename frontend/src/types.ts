export type InventoryItem = {
  size: string;
  quantity: number;
};

export type Product = {
  product_id: string;
  name: string;
  garment_type: string;
  description: string;
  colors: string[];
  search_tags: string[];
  image_file_path: string;
  image_url: string;
  price: number;
  inventory: InventoryItem[];
  total_stock: number;
};
