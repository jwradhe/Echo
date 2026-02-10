// Post Composer Toggle
const composerBtn = document.getElementById('composerBtn');
const composerForm = document.getElementById('composerForm');
const cancelBtn = document.getElementById('cancelBtn');
const postBtn = document.getElementById('postBtn');
const postContent = document.getElementById('postContent');
const charCount = document.getElementById('charCount');

composerBtn.addEventListener('click', () => {
    composerBtn.classList.add('d-none');
    composerForm.classList.remove('d-none');
    postContent.focus();
});

cancelBtn.addEventListener('click', () => {
    composerForm.classList.add('d-none');
    composerBtn.classList.remove('d-none');
    postContent.value = '';
    charCount.textContent = '0/500';
});

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
