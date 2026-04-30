const API_BASE = '/api';

// DOM Elements
const searchInput = document.getElementById('searchInput');
const manufacturerSelect = document.getElementById('manufacturerSelect');
const categorySelect = document.getElementById('categorySelect');
const propWater = document.getElementById('propWater');
const propPet = document.getElementById('propPet');
const propClean = document.getElementById('propClean');
const propRecycled = document.getElementById('propRecycled');
const typeChenille = document.getElementById('typeChenille');
const typeBraided = document.getElementById('typeBraided');
const typeVelvet = document.getElementById('typeVelvet');
const typeBoucle = document.getElementById('typeBoucle');
const typeLeather = document.getElementById('typeLeather');
const typeKnitted = document.getElementById('typeKnitted');
const missingPrice = document.getElementById('missingPrice');
const martindaleSlider = document.getElementById('martindaleSlider');
const martindaleValue = document.getElementById('martindaleValue');

const fabricsGrid = document.getElementById('fabricsGrid');
const resultCount = document.getElementById('resultCount');
const loader = document.getElementById('loader');

const colorModal = document.getElementById('colorModal');
const closeModal = document.getElementById('closeModal');
const modalTitle = document.getElementById('modalTitle');
const modalColorsGrid = document.getElementById('modalColorsGrid');

// State
let fabrics = [];
let debounceTimer;

// Init
async function init() {
    await fetchFilters();
    await fetchFabrics();
    setupEventListeners();
}

async function fetchFilters() {
    try {
        const res = await fetch(`${API_BASE}/filters`);
        const data = await res.json();
        
        data.manufacturers.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m; opt.textContent = m;
            manufacturerSelect.appendChild(opt);
        });
        
        data.categories.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c; opt.textContent = c;
            categorySelect.appendChild(opt);
        });

        // Set slider max
        if(data.max_martindale) {
            martindaleSlider.max = data.max_martindale;
        }
    } catch(e) {
        console.error("Filter init error:", e);
    }
}

async function fetchFabrics() {
    loader.style.display = 'flex';
    fabricsGrid.innerHTML = '';
    
    try {
        const params = new URLSearchParams();
        if(searchInput.value) params.append('q', searchInput.value);
        if(manufacturerSelect.value) params.append('manufacturer', manufacturerSelect.value);
        if(categorySelect.value) params.append('category', categorySelect.value);
        if(propWater.checked) params.append('property', 'Водоотталкивание');
        if(propPet.checked) params.append('property', 'Антикоготь');
        if(propClean.checked) params.append('property', 'Легкая чистка');
        if(propRecycled.checked) params.append('property', 'Переработанный полиэстер');

        if(typeChenille.checked) params.append('type', 'Шенилл');
        if(typeBraided.checked) params.append('type', 'Рогожка');
        if(typeVelvet.checked) params.append('type', 'Велюр / Микровелюр');
        if(typeBoucle.checked) params.append('type', 'Букле');
        if(typeLeather.checked) params.append('type', 'Экокожа');
        if(typeKnitted.checked) params.append('type', 'Трикотаж');

        if(missingPrice.checked) params.append('missing_price_only', true);
        if(martindaleSlider.value > 0) params.append('min_martindale', martindaleSlider.value);
        
        const res = await fetch(`${API_BASE}/fabrics?${params.toString()}`);
        fabrics = await res.json();
        
        resultCount.textContent = fabrics.length;
        renderFabrics();
    } catch (e) {
        console.error('Error fetching fabrics:', e);
    } finally {
        loader.style.display = 'none';
    }
}

function renderFabrics() {
    fabricsGrid.innerHTML = '';
    
    fabrics.forEach(f => {
        const _m = f.martindale ? f.martindale.toLocaleString('ru-RU') : '—';
        const _d = f.density ? f.density : '—';
        const _p = f.missing_price || typeof f.price !== 'number' ? `<span class="price-missing">Уточнить</span>` : `$${f.price.toFixed(2)}`;
        
        const _ft = f.fabric_type || 'Не указан';
        const _propsArray = f.properties ? f.properties.split(',').map(s => s.trim()).filter(s => s) : [];
        const _propsHtml = _propsArray.length > 0 
           ? _propsArray.map(p => `<span style="background:#eef2ff; color:#4338ca; padding:4px 8px; border-radius:12px; font-size:0.75em; margin-right:4px; margin-bottom:4px; font-weight:500; border:1px solid #c7d2fe;">${p}</span>`).join('') 
           : '<span style="font-size:0.85em; color:#9ca3af;">Нет данных</span>';

        const mainImg = f.image_url ? `<img src="${f.image_url}" class="card-main-image" alt="${f.name}" onerror="this.style.display='none'" style="width:100%; height:150px; object-fit:cover; border-radius:12px;">` : '';
        const siteLink = f.product_url ? `<a href="${f.product_url}" target="_blank" class="btn-link" style="display:inline-block; margin-top:8px; margin-bottom:8px; color:#4f46e5; text-decoration:none; font-weight:600; width: 100%; text-align: center; border: 1px solid #4f46e5; padding: 8px; border-radius: 8px; box-sizing: border-box;">Смотреть на сайте</a>` : '';

        const card = document.createElement('div');
        card.className = 'fabric-card';
        card.innerHTML = `
            ${mainImg}
            <div class="card-header" style="margin-top: 10px;">
                <div>
                    <div class="card-manufacturer">${f.manufacturer}</div>
                    <div class="card-title">${f.name}</div>
                </div>
            </div>
            
            <div contenteditable="true" class="card-price" data-id="${f.id}" title="Click to edit price">${_p}</div>
            
            <div class="card-specs">
                <div class="spec-row">
                    <span>Тест Мартиндейла:</span>
                    <strong>${_m}</strong>
                </div>
                <div class="spec-row">
                    <span>Плотность (г/м2):</span>
                    <strong>${_d}</strong>
                </div>
                <div class="spec-row">
                    <span>Категория:</span>
                    <strong>${f.category || '—'}</strong>
                </div>
                <div class="spec-row">
                    <span>Тип:</span>
                    <strong>${_ft}</strong>
                </div>
            </div>

            <div class="card-props" style="margin-bottom: 15px; margin-top: 10px;">
                <div style="font-size: 0.8em; color: #6b7280; margin-bottom: 6px;">Свойства:</div>
                <div style="display:flex; flex-wrap:wrap;">${_propsHtml}</div>
            </div>
            
            <button class="btn-colors" onclick="openColors(${f.id})" style="margin-bottom: 8px;">Галерея цветов (${f.colors.length})</button>
            ${siteLink}
        `;
        fabricsGrid.appendChild(card);
    });

    // Add price edit listeners
    document.querySelectorAll('.card-price').forEach(el => {
        el.addEventListener('blur', handlePriceEdit);
        el.addEventListener('keydown', (e) => {
            if(e.key === 'Enter') {
                e.preventDefault();
                el.blur();
            }
        });
    });
}

async function handlePriceEdit(e) {
    const el = e.target;
    // extract digits and valid decimal points
    const valText = el.textContent.replace('$', '').replace(',', '.').replace(/[^\d.]/g, '');
    if(!valText) return;
    const valObj = parseFloat(valText);
    const id = el.getAttribute('data-id');

    try {
        const res = await fetch(`${API_BASE}/fabrics/${id}/price`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({price: valObj})
        });
        if(res.ok) {
            el.innerHTML = `$${valObj.toFixed(2)}`;
            el.style.borderColor = '#10b981';
            setTimeout(() => el.style.borderColor = 'transparent', 1500);
        }
    } catch(err) {
        console.error(err);
    }
}

function openColors(fabricId) {
    const f = fabrics.find(x => x.id === fabricId);
    if(!f) return;
    
    modalTitle.textContent = `${f.manufacturer} - ${f.name} Цвета`;
    modalColorsGrid.innerHTML = '';
    
    if(f.colors.length === 0) {
        modalColorsGrid.innerHTML = '<p>Фотографии цветов отсутствуют.</p>';
    } else {
        f.colors.forEach(c => {
            const item = document.createElement('div');
            item.className = 'color-item';
            // Use image_url from the database directly
            let imgUrl = c.image_url ? c.image_url : 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iIzMzMyIvPgo8dGV4dCB4PSI1MCIgeT0iNTAiIGZpbGw9IiM3NzciIGZvbnQtZmFtaWx5PSJzYW5zLXNlcmlmIiBmb250LXNpemU9IjE0IiBtextLWFuY2hvcj0ibWlkZGxlIiBhbGlnbm1lbnQtYmFzZWxpbmU9Im1pZGRsZSI+Tm8gSW1hZ2U8L3RleHQ+PC9zdmc+';

            item.innerHTML = `
                <img src="${imgUrl}" alt="${c.color_name}" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iIzMzMyIvPgo8dGV4dCB4PSI1MCIgeT0iNTAiIGZpbGw9IiM3NzciIGZvbnQtZmFtaWx5PSJzYW5zLXNlcmlmIiBmb250LXNpemU9IjE0IiBtextLWFuY2hvcj0ibWlkZGxlIiBhbGlnbm1lbnQtYmFzZWxpbmU9Im1pZGRsZSI+Tm8gSW1hZ2U8L3RleHQ+PC9zdmc+'">
                <div class="color-name">${c.color_name}</div>
            `;
            modalColorsGrid.appendChild(item);
        });
    }
    
    colorModal.classList.add('active');
}

closeModal.addEventListener('click', () => colorModal.classList.remove('active'));
colorModal.addEventListener('click', (e) => {
    if(e.target === colorModal) {
        colorModal.classList.remove('active');
    }
});

function debounceSearch() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
        fetchFabrics();
    }, 400);
}

function setupEventListeners() {
    searchInput.addEventListener('input', debounceSearch);
    manufacturerSelect.addEventListener('change', fetchFabrics);
    categorySelect.addEventListener('change', fetchFabrics);
    propWater.addEventListener('change', fetchFabrics);
    propPet.addEventListener('change', fetchFabrics);
    propClean.addEventListener('change', fetchFabrics);
    propRecycled.addEventListener('change', fetchFabrics);
    typeChenille.addEventListener('change', fetchFabrics);
    typeBraided.addEventListener('change', fetchFabrics);
    typeVelvet.addEventListener('change', fetchFabrics);
    typeBoucle.addEventListener('change', fetchFabrics);
    typeLeather.addEventListener('change', fetchFabrics);
    typeKnitted.addEventListener('change', fetchFabrics);
    missingPrice.addEventListener('change', fetchFabrics);
    
    martindaleSlider.addEventListener('input', (e) => {
        martindaleValue.textContent = e.target.value > 0 ? `от ${parseInt(e.target.value).toLocaleString('ru-RU')} циклов` : '0 циклов';
    });
    martindaleSlider.addEventListener('change', fetchFabrics);
}

// Start
init();
