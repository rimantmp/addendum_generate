/**
 * AG-PUPUK SweetAlert2 Custom Enterprise Helper
 * Menangani notifikasi status (Tambah, Edit, Hapus) dan dialog konfirmasi interaktif.
 */

// 1. Notifikasi Flash Message Otomatis
function triggerFlashAlert(category, message) {
  if (!message || typeof Swal === 'undefined') return;

  let title = 'Informasi';
  let icon = 'info';
  let confirmColor = '#0f766e';

  if (category === 'success') {
    title = 'Berhasil!';
    icon = 'success';
    confirmColor = '#0f766e';
  } else if (category === 'danger' || category === 'error') {
    title = 'Perhatian!';
    icon = 'error';
    confirmColor = '#dc2626';
  } else if (category === 'warning') {
    title = 'Peringatan!';
    icon = 'warning';
    confirmColor = '#d97706';
  }

  Swal.fire({
    icon: icon,
    title: title,
    text: message,
    confirmButtonColor: confirmColor,
    confirmButtonText: 'Selesai',
    timer: category === 'success' ? 3500 : undefined,
    timerProgressBar: category === 'success',
    showCloseButton: true,
    customClass: {
      popup: 'swal2-enterprise-popup'
    }
  });
}

// 2. Dialog Konfirmasi Penghapusan Interaktif
function confirmDelete(e, formOrTarget, customMessage, customTitle) {
  if (e && e.preventDefault) {
    e.preventDefault();
  }

  const title = customTitle || 'Konfirmasi Hapus Data';
  const text = customMessage || 'Apakah Anda yakin ingin menghapus data ini? Tindakan ini bersifat permanen dan tidak dapat dibatalkan.';

  Swal.fire({
    title: title,
    text: text,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#dc2626',
    cancelButtonColor: '#64748b',
    confirmButtonText: 'Ya, Hapus Sekarang',
    cancelButtonText: 'Batal',
    reverseButtons: true,
    focusCancel: true,
    customClass: {
      popup: 'swal2-enterprise-popup'
    }
  }).then((result) => {
    if (result.isConfirmed) {
      if (typeof formOrTarget === 'function') {
        formOrTarget();
      } else if (formOrTarget && formOrTarget.tagName === 'FORM') {
        // Submit form tanpa memicu handler onsubmit kembali
        HTMLFormElement.prototype.submit.call(formOrTarget);
      } else if (formOrTarget && formOrTarget.form) {
        HTMLFormElement.prototype.submit.call(formOrTarget.form);
      }
    }
  });

  return false;
}

// 3. Dialog Konfirmasi Aksi Penting (Restore / Simpan)
function confirmAction(e, formOrTarget, title, message, confirmBtnText = 'Lanjutkan', confirmColor = '#0f766e') {
  if (e && e.preventDefault) {
    e.preventDefault();
  }

  Swal.fire({
    title: title,
    text: message,
    icon: 'question',
    showCancelButton: true,
    confirmButtonColor: confirmColor,
    cancelButtonColor: '#64748b',
    confirmButtonText: confirmBtnText,
    cancelButtonText: 'Batal',
    reverseButtons: true,
    customClass: {
      popup: 'swal2-enterprise-popup'
    }
  }).then((result) => {
    if (result.isConfirmed) {
      if (typeof formOrTarget === 'function') {
        formOrTarget();
      } else if (formOrTarget && formOrTarget.tagName === 'FORM') {
        HTMLFormElement.prototype.submit.call(formOrTarget);
      } else if (formOrTarget && formOrTarget.form) {
        HTMLFormElement.prototype.submit.call(formOrTarget.form);
      }
    }
  });

  return false;
}
