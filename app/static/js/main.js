// Post Composer Toggle
const postBtn = document.getElementById('postBtn');
const postContent = document.getElementById('postContent');
const charCount = document.getElementById('charCount');


// Rensa composer när modalen öppnas
const composerModal = document.getElementById('composerModal');
if (composerModal) {
    composerModal.addEventListener('show.bs.modal', () => {
        const textarea = document.getElementById('postContent');
        const charCount = document.getElementById('charCount');
        if (textarea) textarea.value = '';
        if (charCount) charCount.textContent = '0/500';
    });

    // Teckenräknare
    const postContent = document.getElementById('postContent');
    if (postContent) {
        postContent.addEventListener('input', () => {
            document.getElementById('charCount').textContent = `${postContent.value.length}/500`;
        });
    }
}

// Character counter
postContent.addEventListener('input', () => {
    const length = postContent.value.length;
    charCount.textContent = `${length}/500`;
    postBtn.disabled = length === 0 || length > 500;
});

// Post submission
postBtn.addEventListener('click', async () => {
    const content = postContent.value.trim();
    if (!content) return;

    try {
        const response = await fetch('/api/posts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ content }),
        });

        if (response.ok) {
            location.reload();
        }
    } catch (error) {
        console.error('Error creating post:', error);
    }
});

// Like/Bookmark actions
document.addEventListener('click', async (e) => {
    const actionBtn = e.target.closest('.action-btn');
    if (!actionBtn) return;

    const postCard = actionBtn.closest('.post-card');
    const postId = postCard.dataset.postId;
    const action = actionBtn.dataset.action;

    if (!action) return;

    try {
        const response = await fetch(`/api/posts/${postId}/${action}`, {
            method: 'POST',
        });

        if (response.ok) {
            const post = await response.json();
            
            if (action === 'like') {
                const icon = actionBtn.querySelector('i');
                const count = actionBtn.querySelector('.like-count');
                
                if (post.isLiked) {
                    icon.classList.remove('bi-heart');
                    icon.classList.add('bi-heart-fill');
                    actionBtn.classList.add('liked');
                } else {
                    icon.classList.remove('bi-heart-fill');
                    icon.classList.add('bi-heart');
                    actionBtn.classList.remove('liked');
                }
                count.textContent = post.likes;
            } else if (action === 'bookmark') {
                const icon = actionBtn.querySelector('i');
                
                if (post.isBookmarked) {
                    icon.classList.remove('bi-bookmark');
                    icon.classList.add('bi-bookmark-fill');
                    actionBtn.classList.add('bookmarked');
                } else {
                    icon.classList.remove('bi-bookmark-fill');
                    icon.classList.add('bi-bookmark');
                    actionBtn.classList.remove('bookmarked');
                }
            }
        }
    } catch (error) {
        console.error(`Error ${action}ing post:`, error);
    }
});

// Update all timestamps
document.querySelectorAll('.post-time').forEach(el => {
    const timestamp = el.textContent;
    const date = new Date(timestamp);
    el.textContent = `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
});

window.startInlineEdit = function(btn) {
    const postId = btn.dataset.postId;
    const originalText = btn.dataset.content;

    const postCard = btn.closest('.post-card');
    const contentEl = postCard.querySelector('.post-content');

    contentEl.outerHTML = `
        <div class="inline-edit-container" 
             data-original="${originalText.replace(/"/g, '&quot;')}"
             data-post-id="${postId}">
            <textarea class="form-control mb-2 inline-edit-textarea" maxlength="500">${originalText}</textarea>
            <div class="d-flex gap-2 justify-content-end">
                <small class="text-secondary me-auto inline-edit-charcount">${originalText.length}/500</small>
                <button class="btn btn-outline-secondary btn-sm rounded-pill" onclick="cancelInlineEdit(this)">Avbryt</button>
                <button class="btn btn-primary btn-sm rounded-pill" onclick="saveInlineEdit(this)">Spara</button>
            </div>
        </div>
    `;

    const textarea = postCard.querySelector('.inline-edit-textarea');
    textarea.focus();
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);

    textarea.addEventListener('input', () => {
        postCard.querySelector('.inline-edit-charcount').textContent = `${textarea.value.length}/500`;
    });
}

window.cancelInlineEdit = function(btn) {
    const editContainer = btn.closest('.inline-edit-container');
    const originalText = editContainer.dataset.original;
    const p = document.createElement('p');
    p.className = 'post-content';
    p.textContent = originalText;
    editContainer.replaceWith(p);
}

window.saveInlineEdit = async function(btn) {
    const editContainer = btn.closest('.inline-edit-container');
    const postId = editContainer.dataset.postId;
    const textarea = editContainer.querySelector('.inline-edit-textarea');
    const newContent = textarea.value.trim();

    if (!newContent) return;

    btn.disabled = true;
    btn.textContent = 'Sparar...';

    try {
        const response = await fetch(`/edit_echo/${postId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: newContent })
        });

        if (response.ok) {
            const p = document.createElement('p');
            p.className = 'post-content';
            p.textContent = newContent;
            editContainer.replaceWith(p);
        } else {
            alert('Kunde inte spara. Försök igen.');
            btn.disabled = false;
            btn.textContent = 'Spara';
        }
    } catch (_err) {
        alert('Nätverksfel. Försök igen.');
        btn.disabled = false;
        btn.textContent = 'Spara';
    }
}

window.confirmDelete = function(postId) {
    document.getElementById('deleteForm').action = `/delete_echo/${postId}`;
    new bootstrap.Modal(document.getElementById('deleteModal')).show();
}