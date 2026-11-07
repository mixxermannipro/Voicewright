#include <gtk/gtk.h>
#include <stdio.h>

static void changed(GtkEditable *field, gpointer result_path) {
    const char *text = gtk_entry_get_text(GTK_ENTRY(field));
    FILE *file = fopen(result_path, "w");
    if (file) { fputs(text, file); fclose(file); }
}

int main(int argc, char **argv) {
    gtk_init(&argc, &argv);
    if (argc != 2) return 2;
    GtkWidget *window = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(window), "External Dictation Probe");
    GtkWidget *entry = gtk_entry_new();
    gtk_container_add(GTK_CONTAINER(window), entry);
    g_signal_connect(entry, "changed", G_CALLBACK(changed), argv[1]);
    gtk_widget_show_all(window);
    gtk_widget_grab_focus(entry);
    gtk_main();
    return 0;
}
