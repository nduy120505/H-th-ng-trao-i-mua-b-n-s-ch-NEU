document.addEventListener('DOMContentLoaded', () => {

  const menuBtn     = document.getElementById('menuBtn');
  const sidebar     = document.getElementById('sidebar');
  const overlay     = document.getElementById('sidebarOverlay');
  const closeBtn    = document.getElementById('sidebarClose');

  function openSidebar() {
    sidebar?.classList.add('show');
    overlay?.classList.add('show');
    document.body.style.overflow = 'hidden';
  }
  function closeSidebar() {
    sidebar?.classList.remove('show');
    overlay?.classList.remove('show');
    document.body.style.overflow = '';
  }
  menuBtn?.addEventListener('click', openSidebar);
  closeBtn?.addEventListener('click', closeSidebar);
  overlay?.addEventListener('click', closeSidebar);

  document.querySelectorAll('.sidebar-cat-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const sub  = btn.nextElementSibling;
      const icon = btn.querySelector('.cat-arrow');
      sub?.classList.toggle('open');
      if (icon) icon.textContent = sub?.classList.contains('open') ? '▲' : '▼';
    });
  });

  const avatarBtn  = document.getElementById('avatarBtn');
  const dropdown   = document.getElementById('headerDropdown');

  avatarBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    dropdown?.classList.toggle('show');
  });
  document.addEventListener('click', () => dropdown?.classList.remove('show'));
  dropdown?.addEventListener('click', e => e.stopPropagation());

  document.querySelectorAll('.flash').forEach(el => {
    const close = el.querySelector('.flash-close');
    close?.addEventListener('click', () => el.remove());
    setTimeout(() => el.remove(), 5000);
  });

  document.querySelectorAll('.wishlist-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault(); e.stopPropagation();
      const lid = btn.dataset.lid;
      try {
        const res  = await fetch(`/api/wishlist/${lid}`, { method: 'POST' });
        const data = await res.json();
        btn.textContent = data.added ? 'Đã lưu' : 'Lưu';
        btn.title = data.added ? 'Bỏ yêu thích' : 'Thêm yêu thích';
        btn.classList.toggle('wishlisted', data.added);
        showToast(data.added ? 'Đã thêm vào yêu thích!' : 'Đã bỏ khỏi yêu thích.', data.added ? 'success' : 'info');
      } catch {}
    });
  });

  window.showToast = (msg, type = 'info') => {
    const container = document.querySelector('.flash-container')
      || (() => {
        const c = document.createElement('div');
        c.className = 'flash-container';
        document.body.appendChild(c);
        return c;
      })();
    const el = document.createElement('div');
    el.className = `flash flash-${type}`;
    el.innerHTML = `<span>${msg}</span><button class="flash-close">✕</button>`;
    el.querySelector('.flash-close').addEventListener('click', () => el.remove());
    container.appendChild(el);
    setTimeout(() => el.remove(), 4000);
  };

  const ltypeSelect = document.getElementById('listing_type');
  const priceRow    = document.getElementById('priceRow');
  const exchRow     = document.getElementById('exchangeRow');

  function updateListingFields() {
    if (!ltypeSelect) return;
    const val = ltypeSelect.value;
    if (priceRow) priceRow.style.display = val === 'sell' ? '' : 'none';
    if (exchRow)  exchRow.style.display  = val === 'exchange' ? '' : 'none';
  }
  ltypeSelect?.addEventListener('change', updateListingFields);
  updateListingFields();

  const bookSelect  = document.getElementById('book_id');
  const newBookForm = document.getElementById('newBookForm');
  const newTitleInp = document.getElementById('new_title');

  bookSelect?.addEventListener('change', () => {
    const isNew = bookSelect.value === '__new__';
    if (newBookForm) newBookForm.style.display = isNew ? '' : 'none';
    if (newTitleInp) newTitleInp.required = isNew;
  });

  document.querySelectorAll('.profile-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.profile-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.profile-tab-content').forEach(c => c.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById(tab.dataset.tab)?.classList.add('active');
    });
  });

  const chatBody = document.querySelector('.chat-body');
  if (chatBody) chatBody.scrollTop = chatBody.scrollHeight;

  document.querySelector('.chat-input textarea')?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      e.target.closest('form')?.submit();
    }
  });

  const priceInput = document.getElementById('price');
  priceInput?.addEventListener('blur', () => {
    const v = parseFloat(priceInput.value.replace(/[^0-9.]/g, ''));
    if (!isNaN(v)) priceInput.value = v;
  });

  const currentPath = window.location.pathname;
  document.querySelectorAll('.sidebar-nav a').forEach(a => {
    if (a.getAttribute('href') === currentPath) a.classList.add('active');
  });

});
