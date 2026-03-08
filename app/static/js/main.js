// Post Composer Toggle
const postBtn = document.getElementById('postBtn');
const postContent = document.getElementById('postContent');
const charCount = document.getElementById('charCount');

function formatTimestamp(raw) {
    const date = new Date(raw);
    if (Number.isNaN(date.getTime())) return raw;
    return `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
}

function createCommentElement(comment) {
    const item = document.createElement('div');
    item.className = 'comment-item';

    const avatar = document.createElement('img');
    avatar.className = 'comment-avatar';
    avatar.src = comment.author.avatar;
    avatar.alt = comment.author.name;

    const body = document.createElement('div');
    body.className = 'comment-body';

    const meta = document.createElement('div');
    meta.className = 'comment-meta';

    const author = document.createElement('span');
    author.className = 'comment-author';
    author.textContent = comment.author.name;

    const separator = document.createElement('span');
    separator.className = 'text-secondary';
    separator.textContent = '·';

    const time = document.createElement('span');
    time.className = 'comment-time';
    time.textContent = formatTimestamp(comment.created_at);

    const content = document.createElement('p');
    content.className = 'comment-content';
    content.textContent = comment.content;

    meta.append(author, separator, time);
    body.append(meta, content);
    item.append(avatar, body);
    return item;
}

function parseCommentParticipants(postCard) {
    const raw = postCard?.dataset.commentParticipants;
    if (!raw) return [];
    try {
        const parsed = JSON.parse(raw);
        return Array.isArray(parsed) ? parsed : [];
    } catch (_err) {
        return [];
    }
}

function setThreadClosedState(postCard, isClosed) {
    postCard.dataset.threadClosed = isClosed ? 'true' : 'false';

    const lockIndicator = postCard.querySelector('.thread-locked-indicator');
    if (lockIndicator) {
        lockIndicator.classList.toggle('d-none', !isClosed);
    }

    const note = postCard.querySelector('.thread-closed-note');
    if (note) {
        note.classList.toggle('d-none', !isClosed);
    }

    const lockBtn = postCard.querySelector('.thread-lock-toggle-btn');
    if (lockBtn) {
        lockBtn.dataset.isClosed = isClosed ? 'true' : 'false';
        if (postCard.dataset.threadRestricted === 'true') {
            lockBtn.textContent = 'Svarstråd privat efter utbrytning';
            lockBtn.disabled = true;
        } else {
            lockBtn.textContent = isClosed ? 'Öppna svarstråd' : 'Stäng svarstråd';
            lockBtn.disabled = false;
        }
    }

    const input = postCard.querySelector('.comment-input');
    const submitBtn = postCard.querySelector('.comment-submit-btn');
    const canComment = postCard.dataset.canComment === 'true';
    if (input) {
        input.disabled = !canComment;
        input.placeholder = canComment ? 'Skriv en kommentar...' : 'Svarstråden är stängd.';
    }
    if (submitBtn) {
        submitBtn.disabled = !canComment || !input?.value.trim();
    }
}

function renderSplitParticipants(container, participants) {
    container.innerHTML = '';
    if (!participants.length) {
        const empty = document.createElement('p');
        empty.className = 'split-participants-empty';
        empty.textContent = 'Inga kommentatorer att välja ännu.';
        container.append(empty);
        return;
    }

    participants.forEach((participant) => {
        const check = document.createElement('div');
        check.className = 'form-check';
        check.innerHTML = `
            <input class="form-check-input split-participant-checkbox" type="checkbox" value="${participant.id}" id="split_${participant.id}">
            <label class="form-check-label" for="split_${participant.id}">${participant.name}</label>
        `;
        container.append(check);
    });
}


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
if (postBtn && postContent && charCount) {
    postContent.addEventListener('input', () => {
        const length = postContent.value.length;
        charCount.textContent = `${length}/500`;
        postBtn.disabled = length === 0 || length > 500;
    });

    postBtn.addEventListener('click', async () => {
        const content = postContent.value.trim();
        if (!content) return;

        try {
            const response = await fetch('/api/posts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content }),
            });

            if (response.ok) {
                location.reload();
            }
        } catch (error) {
            console.error('Error creating post:', error);
        }
    });
}

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
    el.textContent = formatTimestamp(el.textContent);
});

document.querySelectorAll('.comment-time').forEach(el => {
    el.textContent = formatTimestamp(el.textContent);
});

document.querySelectorAll('.thread-marker-time').forEach(el => {
    el.textContent = formatTimestamp(el.textContent);
});

document.addEventListener('click', async (e) => {
    const toggleBtn = e.target.closest('.comment-toggle-btn');
    if (toggleBtn) {
        const postCard = toggleBtn.closest('.post-card');
        const section = postCard?.querySelector('.comments-section');
        if (section) {
            section.classList.toggle('d-none');
        }
        return;
    }

    const lockToggleBtn = e.target.closest('.thread-lock-toggle-btn');
    if (lockToggleBtn) {
        const postCard = lockToggleBtn.closest('.post-card');
        const postId = postCard?.dataset.postId;
        if (!postCard || !postId) return;
        if (postCard.dataset.threadRestricted === 'true') {
            showAlert('Svarstråden är privat efter utbrytning.', 'alert-info');
            return;
        }

        const currentState = lockToggleBtn.dataset.isClosed === 'true';
        lockToggleBtn.disabled = true;
        try {
            const response = await fetch(`/api/posts/${postId}/reply-lock`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_closed: !currentState }),
            });
            if (!response.ok) throw new Error('failed');
            const payload = await response.json();
            setThreadClosedState(postCard, Boolean(payload.is_closed));
            showAlert(payload.is_closed ? 'Svarstråden är nu stängd.' : 'Svarstråden är nu öppen.', 'alert-info');
        } catch (_err) {
            showAlert('Kunde inte uppdatera svarstråden.', 'alert-danger');
        } finally {
            lockToggleBtn.disabled = false;
        }
        return;
    }

    const splitBtn = e.target.closest('.discussion-split-open-btn');
    if (splitBtn) {
        const modalEl = document.getElementById('splitDiscussionModal');
        const postCard = splitBtn.closest('.post-card');
        if (!modalEl || !postCard) return;

        const participants = parseCommentParticipants(postCard);
        const modal = new bootstrap.Modal(modalEl);
        const postIdInput = document.getElementById('splitDiscussionPostId');
        const nameInput = document.getElementById('splitDiscussionName');
        const participantsContainer = document.getElementById('splitDiscussionParticipants');
        const submitBtn = document.getElementById('splitDiscussionSubmitBtn');
        if (!postIdInput || !nameInput || !participantsContainer || !submitBtn) return;

        postIdInput.value = postCard.dataset.postId || '';
        nameInput.value = '';
        renderSplitParticipants(participantsContainer, participants);
        submitBtn.disabled = participants.length === 0;
        modal.show();
        return;
    }

    const submitBtn = e.target.closest('.comment-submit-btn');
    if (!submitBtn) return;

    const postCard = submitBtn.closest('.post-card');
    const input = postCard?.querySelector('.comment-input');
    const commentsList = postCard?.querySelector('.comments-list');
    const postId = postCard?.dataset.postId;
    if (!postCard || !input || !commentsList || !postId) return;

    const content = input.value.trim();
    if (!content) return;
    const canComment = postCard.dataset.canComment === 'true';
    if (!canComment) {
        showAlert('Svarstråden är stängd för nya kommentarer.', 'alert-warning');
        return;
    }

    submitBtn.disabled = true;
    const previousLabel = submitBtn.textContent;
    submitBtn.textContent = 'Skickar...';

    try {
        const response = await fetch(`/api/posts/${postId}/comments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content }),
        });

        if (!response.ok) {
            throw new Error('failed');
        }

        const comment = await response.json();
        commentsList.append(createCommentElement(comment));
        input.value = '';

        const charCountEl = postCard.querySelector('.comment-charcount');
        if (charCountEl) charCountEl.textContent = '0/500';

        const countEl = postCard.querySelector('.comment-count');
        if (countEl) {
            const current = parseInt(countEl.textContent, 10) || 0;
            countEl.textContent = `${current + 1}`;
        }
    } catch (_err) {
        showAlert('Kunde inte posta kommentaren.', 'alert-danger');
    } finally {
        submitBtn.textContent = previousLabel;
        submitBtn.disabled = !input.value.trim();
    }
});

document.addEventListener('input', (e) => {
    const commentInput = e.target.closest('.comment-input');
    if (!commentInput) return;

    const postCard = commentInput.closest('.post-card');
    const countEl = postCard?.querySelector('.comment-charcount');
    const submitBtn = postCard?.querySelector('.comment-submit-btn');
    const length = commentInput.value.length;
    if (countEl) countEl.textContent = `${length}/500`;
    if (submitBtn) {
        submitBtn.disabled =
            length === 0 || length > 500 || postCard?.dataset.canComment !== 'true';
    }
});

const splitDiscussionSubmitBtn = document.getElementById('splitDiscussionSubmitBtn');
if (splitDiscussionSubmitBtn) {
    splitDiscussionSubmitBtn.addEventListener('click', async () => {
        const modalEl = document.getElementById('splitDiscussionModal');
        const postIdInput = document.getElementById('splitDiscussionPostId');
        const nameInput = document.getElementById('splitDiscussionName');
        const participantsContainer = document.getElementById('splitDiscussionParticipants');
        if (!modalEl || !postIdInput || !nameInput || !participantsContainer) return;

        const selected = Array.from(
            participantsContainer.querySelectorAll('.split-participant-checkbox:checked')
        ).map((el) => el.value);

        if (!selected.length) {
            showAlert('Välj minst en annan deltagare.', 'alert-warning');
            return;
        }

        splitDiscussionSubmitBtn.disabled = true;
        const previousText = splitDiscussionSubmitBtn.textContent;
        splitDiscussionSubmitBtn.textContent = 'Skapar...';

        try {
            const response = await fetch(`/api/posts/${postIdInput.value}/discussion-groups`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: nameInput.value.trim(),
                    participant_user_ids: selected,
                }),
            });

            if (!response.ok) {
                throw new Error('failed');
            }
            const payload = await response.json();
            bootstrap.Modal.getInstance(modalEl)?.hide();
            const postCard = document.querySelector(`.post-card[data-post-id="${postIdInput.value}"]`);
            if (postCard) {
                postCard.dataset.threadRestricted = 'true';
                postCard.dataset.canComment = 'true';
                setThreadClosedState(postCard, true);
            }
            showAlert(`Diskussion "${payload.name}" skapad.`, 'alert-success');
        } catch (_err) {
            showAlert('Kunde inte bryta ut diskussionen.', 'alert-danger');
        } finally {
            splitDiscussionSubmitBtn.disabled = false;
            splitDiscussionSubmitBtn.textContent = previousText;
        }
    });
}

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


function showAlert(message, type, openModal) {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        console.error('No element with id "toast-container" found');
        return;
    }

    // Define Bootstrap alert background colors
    const alertColors = {
        "alert-success": "bg-success text-white",
        "alert-danger": "bg-danger text-white",
        "alert-warning": "bg-warning text-dark",
        "alert-info": "bg-info text-dark"
    };

    // Define progress bar colors (matching alert colors)
    const progressColors = {
        "alert-success": "bg-success",
        "alert-danger": "bg-danger",
        "alert-warning": "bg-warning",
        "alert-info": "bg-info"
    };

    const bgColor = alertColors[type] || "bg-secondary text-white";
    const progressColor = progressColors[type] || "bg-primary";

    // Create Toast Element
    const toast = document.createElement('div');
    toast.className = `toast show ${bgColor} p-3 rounded shadow position-relative`;
    toast.innerHTML = `
        <div class="toast-body d-flex justify-content-between align-items-center">
            <span>${message}</span>
            <button type="button" class="btn-close ms-3" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="progress position-absolute bottom-0 start-0 w-100">
            <div class="progress-bar progress-bar-striped ${progressColor}" role="progressbar"></div>
        </div>
    `;

    toastContainer.appendChild(toast);

    // Progress Bar Animation
    const progressBar = toast.querySelector('.progress-bar');
    progressBar.style.width = "100%"; // Start full
    setTimeout(() => {
        progressBar.style.transition = "width 5s linear";
        progressBar.style.width = "0%";
    }, 100);

    // Remove toast after progress ends
    setTimeout(() => {
        toast.remove();
    }, 5100);

    // Remove on close button click
    toast.querySelector('.btn-close').addEventListener('click', () => {
        toast.remove();
    });

    // Open modal
    if (openModal) {
        const modal = new bootstrap.Modal(document.getElementById(openModal));
        modal.show();
    }
}

window.showAlert = showAlert;

const profileBio = document.getElementById('profile_bio');
const profileBioCount = document.getElementById('profileBioCount');

if (profileBio && profileBioCount) {
    profileBio.addEventListener('input', () => {
        profileBioCount.textContent = `${profileBio.value.length}/500`;
    });
}
