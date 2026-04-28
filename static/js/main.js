document.addEventListener('DOMContentLoaded', () => {
  const menuBtn = document.getElementById('menuBtn');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  const closeBtn = document.getElementById('sidebarClose');

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

  document.querySelectorAll('.sidebar-cat-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const sub = btn.nextElementSibling;
      const icon = btn.querySelector('.cat-arrow');
      sub?.classList.toggle('open');
      if (icon) icon.textContent = sub?.classList.contains('open') ? '▲' : '▼';
    });
  });

  const avatarBtn = document.getElementById('avatarBtn');
  const dropdown = document.getElementById('headerDropdown');
  avatarBtn?.addEventListener('click', (event) => {
    event.stopPropagation();
    dropdown?.classList.toggle('show');
  });
  dropdown?.addEventListener('click', (event) => event.stopPropagation());
  document.addEventListener('click', () => dropdown?.classList.remove('show'));

  document.querySelectorAll('.flash').forEach((el) => {
    el.querySelector('.flash-close')?.addEventListener('click', () => el.remove());
    setTimeout(() => el.remove(), 5000);
  });

  window.showToast = (msg, type = 'info') => {
    const container = document.querySelector('.flash-container') || (() => {
      const element = document.createElement('div');
      element.className = 'flash-container';
      document.body.appendChild(element);
      return element;
    })();

    const el = document.createElement('div');
    el.className = `flash flash-${type}`;
    el.innerHTML = `<span>${msg}</span><button class="flash-close">✕</button>`;
    el.querySelector('.flash-close')?.addEventListener('click', () => el.remove());
    container.appendChild(el);
    setTimeout(() => el.remove(), 4000);
  };

  document.querySelectorAll('.wishlist-btn').forEach((btn) => {
    btn.addEventListener('click', async (event) => {
      event.preventDefault();
      event.stopPropagation();
      const lid = btn.dataset.lid;
      try {
        const res = await fetch(`/api/wishlist/${lid}`, { method: 'POST' });
        const data = await res.json();
        const added = Boolean(data.added);
        btn.textContent = added ? 'Đã lưu tin' : 'Lưu tin';
        btn.title = added ? 'Bỏ khỏi yêu thích' : 'Thêm vào yêu thích';
        btn.classList.toggle('wishlisted', added);
        showToast(added ? 'Đã thêm vào yêu thích.' : 'Đã bỏ khỏi yêu thích.', added ? 'success' : 'info');
      } catch (error) {
        showToast('Không thể cập nhật yêu thích lúc này.', 'warning');
      }
    });
  });

  const listingTypeSelect = document.getElementById('listing_type');
  const priceRow = document.getElementById('priceRow');
  const exchangeRow = document.getElementById('exchangeRow');
  const updateListingFields = () => {
    if (!listingTypeSelect) return;
    const value = listingTypeSelect.value;
    if (priceRow) priceRow.style.display = value === 'sell' ? '' : 'none';
    if (exchangeRow) exchangeRow.style.display = value === 'exchange' ? '' : 'none';
  };
  listingTypeSelect?.addEventListener('change', updateListingFields);
  updateListingFields();

  const bookSelect = document.getElementById('book_id');
  const newBookForm = document.getElementById('newBookForm');
  const newTitleInput = document.getElementById('new_title');
  const existingCoverImageField = document.getElementById('existingCoverImageField');
  const updateBookFields = () => {
    if (!bookSelect) return;
    const isNew = bookSelect.value === '__new__';
    if (newBookForm) newBookForm.style.display = isNew ? '' : 'none';
    if (newTitleInput) newTitleInput.required = isNew;
    if (existingCoverImageField) existingCoverImageField.style.display = isNew ? 'none' : '';
  };
  bookSelect?.addEventListener('change', updateBookFields);
  updateBookFields();

  document.querySelectorAll('.profile-tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.profile-tab').forEach((item) => item.classList.remove('active'));
      document.querySelectorAll('.profile-tab-content').forEach((item) => item.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById(tab.dataset.tab)?.classList.add('active');
    });
  });

  const chatBody = document.querySelector('.chat-body');
  if (chatBody) chatBody.scrollTop = chatBody.scrollHeight;

  document.querySelector('.chat-input textarea')?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      event.target.closest('form')?.submit();
    }
  });

  const priceInput = document.getElementById('price');
  priceInput?.addEventListener('blur', () => {
    const value = parseFloat(priceInput.value.replace(/[^0-9.]/g, ''));
    if (!Number.isNaN(value)) priceInput.value = value;
  });

  const currentPath = window.location.pathname;
  document.querySelectorAll('.sidebar-nav a, .header-quicklink').forEach((link) => {
    if (link.getAttribute('href') === currentPath) link.classList.add('active');
  });
});
