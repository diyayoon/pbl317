/* Central mock catalog. Replace this module with Flask API responses later. */
window.TA_DATA = {
    categories: [
        ['electronics', 'Elektronik', 'assets/categories/electronics.svg'],
        ['computer', 'Laptop & Komputer', 'assets/categories/computer.svg'],
        ['phone', 'Handphone & Tablet', 'assets/categories/phone.svg'],
        ['men', 'Fashion Pria', 'assets/categories/men.svg'],
        ['women', 'Fashion Wanita', 'assets/categories/women.svg'],
        ['shoes', 'Sepatu', 'assets/categories/shoes.svg'],
        ['bags', 'Tas', 'assets/categories/bags.svg'],
        ['beauty', 'Beauty & Perawatan', 'assets/categories/beauty.svg'],
        ['health', 'Kesehatan', 'assets/categories/health.svg'],
        ['home', 'Rumah Tangga', 'assets/categories/home.svg'],
        ['baby', 'Ibu & Anak', 'assets/categories/baby.svg'],
        ['gaming', 'Gaming', 'assets/categories/gaming.svg'],
        ['hobby', 'Hobi & Koleksi', 'assets/categories/hobby.svg'],
        ['auto', 'Otomotif', 'assets/categories/auto.svg'],
        ['food', 'Makanan & Minuman', 'assets/categories/food.svg'],
        ['services', 'Perlengkapan & Tools', 'assets/categories/tools.svg']
    ],

    stores: [
        { id: 1, name: 'Aurora Tech', rating: 4.9, city: 'Batam', followers: 12800 },
        { id: 2, name: 'BlueBerry Store', rating: 4.8, city: 'Jakarta', followers: 9200 },
        { id: 3, name: 'Elara Fashion', rating: 4.9, city: 'Bandung', followers: 15400 },
        { id: 4, name: 'Frosty Goods', rating: 4.7, city: 'Surabaya', followers: 6100 },
        { id: 5, name: 'Azure Gadget', rating: 4.8, city: 'Medan', followers: 8700 }
    ],

    products: [
        {
            id: 1,
            storeId: 1,
            name: 'Aurora Wireless Headset',
            category: 'electronics',
            price: 399000,
            stock: 23,
            rating: 4.9,
            sold: 1200,
            icon: '🎧',
            desc: 'Headset wireless ringan dengan audio jernih untuk kerja dan gaming.',
            variants: ['Ice Blue', 'White', 'Midnight']
        },
        {
            id: 2,
            storeId: 2,
            name: 'Mechanical Keyboard Ice',
            category: 'gaming',
            price: 549000,
            stock: 18,
            rating: 4.8,
            sold: 860,
            icon: '⌨️',
            desc: 'Keyboard mechanical compact dengan tactile switch dan icy backlight.',
            variants: ['Blue Switch', 'Brown Switch']
        },
        {
            id: 3,
            storeId: 5,
            name: 'Crystal Mini Fan',
            category: 'electronics',
            price: 149000,
            stock: 42,
            rating: 4.7,
            sold: 2400,
            icon: '🌀',
            desc: 'Kipas mini portable 5 kecepatan dengan display digital.',
            variants: ['Putih', 'Biru', 'Pink']
        },
        {
            id: 4,
            storeId: 3,
            name: 'Cloud Knit Cardigan',
            category: 'women',
            price: 229000,
            stock: 31,
            rating: 4.9,
            sold: 730,
            icon: '🧥',
            desc: 'Cardigan knit lembut untuk daily wear dengan warna pastel.',
            variants: ['S', 'M', 'L']
        },
        {
            id: 5,
            storeId: 4,
            name: 'Frost Glass Tumbler',
            category: 'home',
            price: 89000,
            stock: 56,
            rating: 4.8,
            sold: 3100,
            icon: '🥤',
            desc: 'Tumbler kaca minimalis dengan sleeve frosted.',
            variants: ['450ml', '600ml']
        },
        {
            id: 6,
            storeId: 3,
            name: 'Snow Canvas Bag',
            category: 'bags',
            price: 179000,
            stock: 27,
            rating: 4.8,
            sold: 940,
            icon: '👜',
            desc: 'Tas kanvas clean dengan kompartemen laptop.',
            variants: ['Cream', 'Ice Blue']
        },
        {
            id: 7,
            storeId: 4,
            name: 'Arctic Skin Set',
            category: 'beauty',
            price: 259000,
            stock: 15,
            rating: 4.7,
            sold: 620,
            icon: '🧴',
            desc: 'Mock skincare set untuk prototype UI.',
            variants: ['Normal', 'Dry']
        },
        {
            id: 8,
            storeId: 5,
            name: 'Glacier Smartwatch',
            category: 'electronics',
            price: 799000,
            stock: 12,
            rating: 4.9,
            sold: 510,
            icon: '⌚',
            desc: 'Smartwatch mock dengan AMOLED display dan activity tracking.',
            variants: ['40mm', '44mm']
        }
    ]
};
