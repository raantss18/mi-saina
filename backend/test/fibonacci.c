#include <stdio.h>

int fibonacci(int n) {
    if (n <= 0) return 0;
    if (n == 1 || n == 2) return 1;
    
    int a = 0, b = 1;
    int temp;
    
    for (int i = 3; i <= n; i++) {
        temp = a + b;
        a = b;
        b = temp;
    }
    return b;
}

int main() {
    int n;
    printf("Entrez un entier positif (n) : ");
    scanf("%d", &n);
    
    if (n < 0) {
        printf("Erreur : n doit être positif.\n");
        return 1;
    }
    
    printf("Le %d-ième terme de la suite de Fibonacci est : %d\n", n, fibonacci(n));
    return 0;
}
