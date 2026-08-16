// Tag Input Component
// A reusable component for managing tags/chips with add/remove functionality

class TagInput {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.error(`TagInput: Container with ID "${containerId}" not found`);
      return;
    }

    this.options = {
      placeholder: options.placeholder || 'Add item...',
      maxTags: options.maxTags || null,
      allowDuplicates: options.allowDuplicates || false,
      onChange: options.onChange || null,
      ...options
    };

    this.tags = [];
    this.init();
  }

  init() {
    // Build the component structure from template
    this.container.classList.add('tag-input-container');

    const template = document.getElementById('tag-input-template');
    const clone = template.content.cloneNode(true);

    this.container.appendChild(clone);

    this.tagList = this.container.querySelector('.tag-list');
    this.inputField = this.container.querySelector('.tag-input-field');
    this.addButton = this.container.querySelector('.tag-add-btn');
    this.countDisplay = this.container.querySelector('.tag-count');

    // Set placeholder
    this.inputField.placeholder = this.options.placeholder;

    // Bind events
    this.addButton.addEventListener('click', () => this.addTag());
    this.inputField.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        this.addTag();
      }
    });

    this.updateCount();
  }

  addTag() {
    const value = this.inputField.value.trim();

    if (!value) {
      return;
    }

    // Check for duplicates
    if (!this.options.allowDuplicates && this.tags.includes(value)) {
      this.inputField.value = '';
      this.inputField.focus();
      return;
    }

    // Check max tags limit
    if (this.options.maxTags && this.tags.length >= this.options.maxTags) {
      this.inputField.value = '';
      return;
    }

    this.tags.push(value);
    this.renderTag(value);
    this.inputField.value = '';
    this.inputField.focus();
    this.updateCount();
    this.triggerChange();
  }

  renderTag(value) {
    const template = document.getElementById('tag-item-template');
    const clone = template.content.cloneNode(true);

    clone.querySelector('.tag-text').textContent = value;

    this.tagList.appendChild(clone);

    // Get reference to the actual element now that it's in the DOM
    const tagElement = this.tagList.lastElementChild;
    const removeBtn = tagElement.querySelector('.tag-remove');
    removeBtn.addEventListener('click', () => this.removeTag(value, tagElement));
  }

  removeTag(value, tagElement) {
    const index = this.tags.indexOf(value);
    if (index > -1) {
      this.tags.splice(index, 1);
      tagElement.remove();
      this.updateCount();
      this.triggerChange();
    }
  }

  updateCount() {
    const count = this.tags.length;
    const label = this.options.countLabel || 'items';
    const singularLabel = this.options.countLabelSingular || label.replace(/s$/, '');

    this.countDisplay.textContent = count === 1
      ? `1 ${singularLabel} configured`
      : `${count} ${label} configured`;
  }

  triggerChange() {
    if (this.options.onChange && typeof this.options.onChange === 'function') {
      this.options.onChange(this.tags);
    }
  }

  setTags(tags) {
    this.clear();
    if (Array.isArray(tags)) {
      tags.forEach(tag => {
        if (tag && tag.trim()) {
          this.tags.push(tag.trim());
          this.renderTag(tag.trim());
        }
      });
    }
    this.updateCount();
  }

  getTags() {
    return [...this.tags];
  }

  clear() {
    this.tags = [];
    this.tagList.innerHTML = '';
    this.updateCount();
  }
}
