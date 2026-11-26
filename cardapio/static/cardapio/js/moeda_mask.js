// Máscara de moeda (R$ 1.234,56) para inputs com [data-mascara="moeda"].
// O usuário digita só números; os dois últimos dígitos são os centavos.
(function () {
    function formatar(digitos) {
        digitos = digitos.replace(/\D/g, '').replace(/^0+(?=\d)/, '');
        if (!digitos) return '';
        while (digitos.length < 3) digitos = '0' + digitos;
        const inteiro = digitos.slice(0, -2).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        return 'R$ ' + inteiro + ',' + digitos.slice(-2);
    }

    function aplicar(input) {
        input.setAttribute('inputmode', 'numeric');
        input.setAttribute('autocomplete', 'off');
        input.addEventListener('input', function () {
            input.value = formatar(input.value);
        });
        input.value = formatar(input.value);
    }

    function iniciar() {
        document.querySelectorAll('input[data-mascara="moeda"]').forEach(aplicar);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', iniciar);
    } else {
        iniciar();
    }
})();
