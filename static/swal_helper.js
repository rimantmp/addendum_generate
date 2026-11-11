/**
 * AG-PUPUK SweetAlert2 Custom Enterprise Helper
 * Anthropic Minimalist Institutional Design System
 * Restrained colors, high contrast (#141413), crisp typography.
 */

// 1. Notifikasi Flash Message Otomatis
function triggerFlashAlert(category, message) {
  if (!message || typeof Swal === 'undefined') return;

  let title = 'Informasi';
  let icon = 'info';
  let confirmColor = '#141413';

  if (category === 'success') {
    title = 'Berhasil';
    icon = 'success';
    confirmColor = '#141413';
  } else if (category === 'danger' || category === 'error') {
    title = 'Perhatian';
    icon = 'error';
    confirmColor = '#991b1b';
  } else if (category === 'warning') {
    title = 'Peringatan';
    icon = 'warning';
    confirmColor = '#141413';
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
    confirmButtonColor: '#991b1b',
    cancelButtonColor: '#141413',
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
function confirmAction(e, formOrTarget, title, message, confirmBtnText = 'Lanjutkan', confirmColor = '#141413') {
  if (e && e.preventDefault) {
    e.preventDefault();
  }

  Swal.fire({
    title: title,
    text: message,
    icon: 'question',
    showCancelButton: true,
    confirmButtonColor: confirmColor,
    cancelButtonColor: '#141413',
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
